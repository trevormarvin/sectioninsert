#!/usr/bin/env python3

'''
Microchip MPASM assembler preprocessor.
c2018  Trevor Marvin  GPLv3

Edit this file to contain paths to your MPASM binary below.

The way this file is set up to run, rename the original 'mpasmx' program to
something else, put this file in its place or link to it, and configure this
program to know where the original file is.  It will run before MPASM and then
chain to it.
'''


import sys, heapq, subprocess, time

ifstack = []
defines = {}
sections = {}
completed_sections = {}
mpasm_prog = '/opt/microchip/mplabx/v4.20/mpasmx/mpasmx_orig'
interim_file = '_pre_processed_file.asm'
inputfilename = None

for entry in sys.argv[1:]:
  if entry[:1] == '-':
    continue     # skip options, but will pass to MPASM later
  inputfilename = entry
  break

# -----------------------------------------------------------------------------

def parse_file(infile, outfile, filename):
  
  global ifstack, defines, sections
  splicebefore = []
  splicebetween = []
  spliceafter = []
  spliceempty = []
  
  #for count, line in enumerate(infile.readlines()):
  count = -1
  while True:
    count += 1
    line = infile.readline()
    if len(line) == 0:
      break
    
    if ';' in line:
      pieces = line.split(';', 1)[0].split()  # remove comment
    else:
      pieces = line.split()
    
    if len(pieces) == 0:
      outfile.write(line)
      continue
    keyword = pieces[0].lower()
    
    if keyword in ['#ifdef', '#ifndef', '#define', '#undefine', '#include',
                   '#insert', '#section', ] and len(pieces) < 2:
      print('PRE-PREPROCESSOR: not enough arguments in ' + filename + \
            ' at line ' + str(count + 1), file=sys.stderr)
      print('- line: ' + line, file=sys.stderr)
      errfile.write('PRE-PREPROCESSOR: not enough arguments in ' + \
                    filename + ' at line ' + str(count + 1) + '\n')
      errfile.write('- line: ' + line + '\n')
      sys.exit(1)
    
    if keyword == '#endif':
      if len(ifstack) == 0:
        print('unmatched ENDIF directive in ' + filename, file=sys.stderr)
        errfile.write('unmatched ENDIF directive in file ' + filename + \
                      ' at line ' + str(count) + '\n')
        sys.exit(1)
      ifstack.pop()
      outfile.write(line)
      continue

    if keyword == '#else':
      if len(ifstack) == 0:
        print('unmatched ELSE directive in ' + filename, file=sys.stderr)
        errfile.write('unmatched ELSE directive in file ' + filename + \
                      ' at line ' + str(count) + '\n')
        sys.exit(1)
      index = len(ifstack) - 1
      if ifstack[index] is True:
        ifstack[index] = False
      elif ifstack[index] is False:
        ifstack[index] = True
    
    if keyword == '#if':
      ifstack.append(None)
      outfile.write(line)
      continue
    
    if keyword == '#ifdef':
      if pieces[1].lower() in defines:
        ifstack.append(True)
      else:
        ifstack.append(False)
      outfile.write(line)
      continue
    
    if keyword == '#ifndef':
      if pieces[1].lower() in defines:
        ifstack.append(False)
      else:
        ifstack.append(True)
      outfile.write(line)
      continue
    
    if keyword == '#define':
      if len(pieces) > 2:
        defines[pieces[1].lower()] = pieces[2]
      else:
        defines[pieces[1].lower()] = None
      outfile.write('; PRE-PREPROCESSOR, caught #DEFINE: ' + \
                    pieces[1].lower() + '\n')
      outfile.write(line)
      continue

    # special case for catching 'set' and 'equ' function
    if (len(pieces) > 2) and (pieces[1].lower() in ['set', 'equ', ]):
      value = ' '.join(pieces[2:]).strip()
      if ';' in value:
        value = value.split(';')[0].strip()
      defines[pieces[0].lower()] = value
      outfile.write("; PRE-PREPROCESSOR, caught 'set' or 'equ': " + \
                    pieces[0].lower() + '\n')
      outfile.write(line)
      continue

    if keyword == '#undefine':
      if pieces[1].lower() in defines:
        del defines[pieces[1].lower()]
      outfile.write('; PRE-PREPROCESSOR, caught #UNDEFINE: ' + \
                    pieces[1].lower() + '\n')
      outfile.write(line)
      continue
    
    if keyword == '#include':
      if len(ifstack) > 0 and False in ifstack:
        # conditional says to not include it
        outfile.write('; PRE-PREPROCESSOR, skipping include directive due to condition stack\n')
        outfile.write(line)
        continue
      recfn = pieces[1]
      if recfn[:1] == '<':
        recfn = recfn[1:-1]
      try:
        recfile = open(recfn, 'r')
      except Exception as msg:
        outfile.write('; PRE-PREPROCESSOR, failed to open include file: ' + \
                      recfn + '\n')
        outfile.write(line)
        print('PRE WARNING: failed to open include file: ' + recfn, file=sys.stderr)
        continue
      # scan the file for "INSERT" and "SECTION" directives, skip if none are in there
      for line2 in recfile.readlines():
        pieces2 = line2.split()
        if len(pieces2) == 0:
          continue
        if pieces2[0].lower() in ['#insert', '#section', '#generate', \
                                  '#splicebefore', '#splicebetween', \
                                  '#spliceafter', '#spliceempty', \
                                  '#endsplice', ]:
          break
      else:
        outfile.write('; PRE-PREPROCESSOR, skipping expanding included file: ' \
                      + recfn + '\n')
        outfile.write(line)
        continue
      recfile.seek(0)
      outfile.write('; PRE-PREPROCESSOR, including: ' + recfn + '\n')
      stack_balance = len(ifstack)
      parse_file(recfile, outfile, recfn)
      if len(ifstack) != stack_balance:
        print('PRE SERIOUS WARNING: conditional stack length altered after ' + \
              'INCLUDE directive in file: ' + recfn, file=sys.stderr)
      recfile.close()
      outfile.write('\n')
      continue
    
    if keyword in ['#insert', '#section', '#generate', '#splicebefore', \
                   '#splicebetween', '#spliceafter', '#spliceempty', \
                   '#endsplice', ]:
      if len(ifstack) > 0 and False in ifstack:
        # conditional says to not compile it, so look for special preprocessor
        # directives to strip out
        outfile.write('; PRE-PREPROCESSOR, skipping special directive due ' + \
                      'to condition stack\n')
        outfile.write('; PRE-PREPROCESSOR: ' + line.strip() + '\n')
        outfile.write('; PRE-PREPROCESSOR: ' + str(ifstack) + '\n')
        if keyword == '#generate':
          outfile.write('; PRE-PREPROCESSOR ERROR: stripping ' + keyword + '\n')
          # need to get to the end of the GENERATE directive
          while True:
            line = infile.readline()
            count += 1
            if len(line) == 0:
              outfile.write('; PRE-PREPROCESSOR ERROR: did not find end of' + \
                            'GENERATE directive in file: ' + filename + '\n')
              print('PRE-PREPROCESSOR ERROR: did not find end of' + \
                    'GENERATE directive in file: ' + filename, file=sys.stderr)
              sys.exit(1)
            if len(line.split()) > 0 and \
               line.split()[0].lower() == '#endgen':
              break
        if keyword in ['#splicebefore', '#splicebetween', '#spliceafter', \
                       '#spliceempty', ]:
          outfile.write('; PRE-PREPROCESSOR ERROR: stripping ' + keyword + '\n')
          # need to get to the end of the section directive
          while True:
            line = infile.readline()
            count += 1
            if len(line) == 0:
              outfile.write('; PRE-PREPROCESSOR ERROR: did not find end of' + \
                            ' a splice directive in file: ' + filename + '\n')
              print('PRE-PREPROCESSOR ERROR: did not find end of' + \
                    ' a splice directive in file: ' + filename, file=sys.stderr)
              sys.exit(1)
            if len(line.split()) > 0 and \
               line.split()[0].lower() == '#endsplice':
              break
        continue
      
      elif keyword == '#insert':
        # form of: #INSERT (macro_name) (section_name) [priority] [macro_arg]...
        sectionName = pieces[2].lower()
        if sectionName in sections:
          if sections[sectionName] is None:
            outfile.write('; PRE-PREPROCESSOR, found INSERT directive after' + \
                          ' SECTION directive in: ' + filename + '\n')
            outfile.write('; PRE-PREPROCESSOR, SECTION directive was in: ' + \
                          completed_sections[sectionName] + '\n')
            print('PRE-PREPROCESSOR ERROR: found INSERT directive after ' + \
                  'SECTION directive in: ' + filename, file=sys.stderr)
            print('PRE-PREPROCESSOR ERROR: SECTION directive was in: ' + \
                  completed_sections[sectionName], file=sys.stderr)
            sys.exit(1)
        else:
          sections[sectionName] = []
        if len(pieces) > 3:
          try:
            priority = float(pieces[3])
          except ValueError:
            outfile.write('; PRE-PREPROCESSOR, bad priority value\n')
            outfile.write(line)
            print('PRE-PREPROCESSOR ERROR: bad priority value in: ' + \
                  filename + ' at line: ' + str(count), file=sys.stderr)
            print('PRE-PREPROCESSOR ERROR: ' + line, file=sys.stderr)
            sys.exit(1)
        else:
          priority = 100.0
        if len(pieces) > 4:
          macroargs = pieces[4:]
        else:
          macroargs = None
        heapq.heappush(sections[sectionName], (priority, pieces[1], macroargs))
        outfile.write('; PRE-PREPROCESSOR, found INSERT directive\n')
        outfile.write('; PRE-PREPROCESSOR: ' + line.strip() + '\n')
        continue
      
      elif keyword == '#splicebefore':
        splicebefore = []
        while True:
          line = infile.readline()
          count += 1
          if len(line) == 0:
            outfile.write('; PRE-PREPROCESSOR ERROR: did not find end of' + \
                          'SPLICEBEFORE directive in file: ' + filename + '\n')
            print('PRE-PREPROCESSOR ERROR: did not find end of' + \
                  'SPLICEBEFORE directive in file: ' + filename, \
                  file=sys.stderr)
            sys.exit(1)
          if len(line.split()) > 0 and \
             line.split()[0].lower() == '#endsplice':
            break
          splicebefore.append(line)
        continue
        
      elif keyword == '#splicebetween':
        splicebetween = []
        while True:
          line = infile.readline()
          count += 1
          if len(line) == 0:
            outfile.write('; PRE-PREPROCESSOR ERROR: did not find end of' + \
                          'SPLICEBETREEN directive in file: ' + filename + '\n')
            print('PRE-PREPROCESSOR ERROR: did not find end of' + \
                  'SPLICEBETWEEN directive in file: ' + filename, \
                  file=sys.stderr)
            sys.exit(1)
          if len(line.split()) > 0 and \
             line.split()[0].lower() == '#endsplice':
            break
          splicebetween.append(line)
        continue

      elif keyword == '#spliceafter':
        spliceafter = []
        while True:
          line = infile.readline()
          count += 1
          if len(line) == 0:
            outfile.write('; PRE-PREPROCESSOR ERROR: did not find end of' + \
                          'SPLICEAFTER directive in file: ' + filename + '\n')
            print('PRE-PREPROCESSOR ERROR: did not find end of' + \
                  'SPLICEAFTER directive in file: ' + filename, \
                  file=sys.stderr)
            sys.exit(1)
          if len(line.split()) > 0 and \
             line.split()[0].lower() == '#endsplice':
            break
          spliceafter.append(line)
        continue

      elif keyword == '#spliceempty':
        spliceempty = []
        while True:
          line = infile.readline()
          count += 1
          if len(line) == 0:
            outfile.write('; PRE-PREPROCESSOR ERROR: did not find end of' + \
                          'SPLICEEMPTY directive in file: ' + filename + '\n')
            print('PRE-PREPROCESSOR ERROR: did not find end of' + \
                  'SPLICEEMPTY directive in file: ' + filename, \
                  file=sys.stderr)
            sys.exit(1)
          if len(line.split()) > 0 and \
             line.split()[0].lower() == '#endsplice':
            break
          spliceempty.append(line)
        continue
        
      elif keyword == '#section':
        # form of: #SECTION (section_name) [macro_args] [...]
        sectionName = pieces[1].lower()
        if not sectionName in sections:
          print('PRE WARNING: no sections for SECTION directive: ' + \
                sectionName, file=sys.stderr)
          outfile.write('; PRE-PREPROCESSOR, WARNING, nothing found for SECTION directive\n')
          outfile.write('; PRE-PREPROCESSOR: ' + line.strip() + '\n')
          if spliceempty:
            outfile.write('; PRE-PREPROCESSOR: empty splice section\n')
            for line in spliceempty:
              outfile.write(line)
        else:
          outfile.write('; PRE-PREPROCESSOR, found SECTION directive\n')
          outfile.write('; PRE-PREPROCESSOR: ' + line.strip() + '\n')
          if len(pieces) > 2:
            macro_args = ' ' + ' '.join(pieces[2:])
          else:
            macro_args = ''
          
          for line in splicebefore:
            outfile.write(line)
          count2 = 1
          
          while sections[sectionName]:
            macro, args = heapq.heappop(sections[sectionName])[1:]
            outfile.write('; PRE-PREPROCESSOR: section: ' + sectionName + \
                          ' inserting macro: ' + macro + '\n')
            if args:    # args taken from the INSERT directive
              outfile.write('\t' + macro + ' ' + ', '.join(args) + '\n')
            else:       # args taken from the SECTION directive
              outfile.write('\t' + macro + macro_args + '\n')
            if len(sections[sectionName]):
              for line in splicebetween:
                outfile.write(substitute(line, count2, filename))
            count2 += 1
          
          for line in spliceafter:
            outfile.write(substitute(line, count2, filename))
        
        sections[sectionName] = None
        completed_sections[sectionName] = filename
        splicebefore = []
        splicebetween = []
        spliceafter = []
        spliceempty = []
        continue
    
      if keyword == '#generate':
        outfile.write('; PRE-PREPROCESSOR, found GENERATE directive\n')
        outfile.write('; PRE-PREPROCESSOR: ' + line.strip() + '\n')
        try:
          fromcount = int(pieces[1])
          tocount = int(pieces[2])
        except:
          outfile.write('; PRE-PREPROCESSOR ERROR: bad GENERATE directive count\n')
          outfile.write('; PRE-PREPROCESSOR: ' + line.strip() + '\n')
          print('PRE-PREPROCESSOR ERROR: bad GENERATE directive count', \
                file=sys.stderr)
          print('PRE-PREPROCESSOR: ' + line.strip(), file=sys.stderr)
          sys.exit(1)
        
        # read for the section we're going to generate/loop
        section = []
        while True:
          line = infile.readline()
          count += 1
          if len(line) == 0:
            outfile.write('; PRE-PREPROCESSOR ERROR: did not find end of' + \
                          'GENERATE directive in file: ' + filename + '\n')
            print('PRE-PREPROCESSOR ERROR: did not find end of' + \
                  'GENERATE directive in file: ' + filename, file=sys.stderr)
            sys.exit(1)
          if len(line.split()) > 0 and \
             line.split()[0].lower() == '#endgen':
            break
          section.append(line)
        
        for count2 in range(fromcount, tocount + 1):
          for line in section:
            outfile.write(substitute(line, count2, filename))
      
      continue
    
    outfile.write(line)
    continue
  
  infile.close()
    
    
# ----------------------------------------------
def substitute(line0, count2, filename):

  while ('{' in line0) and ('}' in line0):
    try:
      line1, line2 = line0.split('{', 1)
      line2, line3 = line2.split('}', 1)
      if line2 == 'i':     # simple substitution for current count
        line0 = line1 + str(count2) + line3
      elif (line2.lower() in defines) and (defines[line2.lower()]):
        # substitution with what's been #DEFINEd, if it exists
        line0 = defines[line2.lower()]
      else:
        for char in line2:
          if char != 'i':
            raise Exception()
        # substitution with the count, but add leading zeros
        line0 = str(count2)
        while len(line0) < len(line2):    # pad till same length
          line2 = '0' + line0
        line0 = line1 + line0 + line3
    except:
      outfile.write('; PRE-PREPROCESSOR ERROR: bad substitution ' + \
                    'data in: ' + filename + '\n')
      outfile.write('; PRE-PREPROCESSOR: ' + line0.strip() + '\n')
      print('PRE-PREPROCESSOR ERROR: bad substitution data in ' + \
            'file: ' + filename, file=sys.stderr)
      print('PRE-PREPROCESSOR: line: ' + line0.strip(), \
            file=sys.stderr)
      sys.exit(1)
  
  return line0


# -----------------------------------------------------------------------------

if not inputfilename:
  print("no file specified")
  sys.exit(1)

# the filename is coming in with quotes on it
if inputfilename[:1] == '"':
  inputfilename = inputfilename.strip('"')

try:
  infile = open(inputfilename, 'r')
except Exception as msg:
  print("failed to import file, error: " + str(msg))
  print("failed to import file: " + str(inputfilename))
  sys.exit(1)

if '.' in inputfilename:
  basename = inputfilename.split('.')[0]
else:
  basename = inputfilename

try:
  outfile = open(interim_file, 'w')
except Exception as msg:
  print("failed to create output file, error: " + str(msg))
  sys.exit(1)

try:
  errfile = open(basename + '.pre.ERR', 'w')
except Exception as msg:
  print("failed to create error file, error: " + str(msg))
  sys.exit(1)

parse_file(infile, outfile, inputfilename)

outfile.close()

bail = False
for sectionName in sections:
  if not sections[sectionName] is None:
    bail = True
    print('PRE ERROR: SECTION directive not found for section: ' + \
          sectionName, file=sys.stderr)
    while sections[sectionName]:
      print('  macro to insert there: ' + \
            heapq.heappop(sections[sectionName])[1], file=sys.stderr)
if bail:
  sys.exit(1)

print('PRE INFO: pre-preprocessor completed, chaining to assembler', \
      file=sys.stderr)

# -----------------------------------------------------------------------------
# pass generated output to assembler program
if mpasm_prog:

  args = []
  args.append(mpasm_prog)
  for entry in sys.argv[1:]:
    if entry[:1] == '-':
      args.append(entry)
  args.append(interim_file)
  
  proc = subprocess.Popen(args)
  
  while proc.poll() is None:
    time.sleep(0.5)
  
  if proc.poll() != 0:
    print('MPASM returned non-zero: ' + str(proc.poll()), file=sys.stderr)
    sys.exit(proc.poll())

else:
  sys.exit(0)

  
