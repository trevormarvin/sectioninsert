#!/usr/bin/env python3

'''
Microchip MPasm assembler preprocessor.
c2018  Trevor Marvin

Edit this file to contain paths to your MPasm binary below.

The way this file is set up to run, rename the original 'mpasmx' program to
something else, put this file in its place or link to it, and configure this
program to know where the original file is.  It will run before MPASM and then
chain to it.
'''


import sys, heapq, subprocess, time

ifstack = []
defines = {}
sections = {}
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
  
  for count, line in enumerate(infile.readlines()):
    
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
      outfile.write(line)
      continue

    if keyword == '#undefine':
      if pieces[1].lower() in defines:
        del defines[pieces[1].lower()]
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
        if pieces2[0].lower() in ['#insert', '#section', ]:
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
        print('PRE SERIOUS WARNING: conditional stack length altered after INCLUDE directive', \
              file=sys.stderr)
      recfile.close()
      outfile.write('\n')
      continue
    
    if keyword in ['#insert', '#section', ]:
      if len(ifstack) > 0 and False in ifstack:
        # conditional says to not compile it, so look for special preprocessor
        # directives to strip out
        outfile.write('; PRE-PREPROCESSOR, skipping special directive due to \
                      condition stack\n')
        outfile.write('; PRE-PREPROCESSOR: ' + line + '\n')
        outfile.write('; PRE-PREPROCESSOR: ' + str(ifstack) + '\n')
        continue
    
      elif keyword == '#insert':
        # form of: #INSERT (macro_name) (section_name) [priority]
        sectionName = pieces[2].lower()
        if sectionName in sections:
          if sections[sectionName] is None:
            outfile.write('; PRE-PREPROCESSOR, found INSERT directive after SECTION directive\n')
            sys.exit(1)
        else:
          sections[sectionName] = []
        if len(pieces) > 3:
          priority = float(pieces[3])
        else:
          priority = 100.0
        heapq.heappush(sections[sectionName], (priority, pieces[1]))
        outfile.write('; PRE-PREPROCESSOR, found INSERT directive\n')
        outfile.write('; PRE-PREPROCESSOR: ' + line + '\n')
        continue
      
      elif keyword == '#section':
        # form of: #SECTION (section_name) [macro_args] [...]
        sectionName = pieces[1].lower()
        if not sectionName in sections:
          print('PRE WARNING: no sections for SECTION directive: ' + \
                sectionName, file=sys.stderr)
          outfile.write('; PRE-PREPROCESSOR, WARNING, nothing found for SECTION directive\n')
          outfile.write('; PRE-PREPROCESSOR: ' + line + '\n')
        else:
          outfile.write('; PRE-PREPROCESSOR, found SECTION directive\n')
          outfile.write('; PRE-PREPROCESSOR: ' + line + '\n')
          if len(pieces) > 2:
            macro_args = ' ' + ' '.join(pieces[2:])
          else:
            macro_args = ''
          while sections[sectionName]:
            macro = heapq.heappop(sections[sectionName])[1]
            outfile.write('\t' + macro + macro_args + '\n')
        sections[sectionName] = None
        continue
    
    outfile.write(line)
    continue
  
  infile.close()
    
    
    
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

  
