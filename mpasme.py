#!/usr/bin/env python3

'''
Microchip MPasm assembler preprocessor.
c2018  Trevor Marvin


Edit this file to contain paths to your Mpasm and Mplink binaries below.

'''


import sys, heapq, subprocess, time

defines = {}
sections = {}
processor = None   # capture the type of processor to send to the linker
mpasm_prog = '/opt/microchip/mplabx/v4.15/mpasmx/mpasmx'
mplink_prog = '/opt/microchip/mplabx/v4.15/mpasmx/mplink'
interim_file = '_pre_processed_file.asm'


# -----------------------------------------------------------------------------

def parse_file(infile, outfile, filename):
  
  global processor
  count = -1
  
  for line in infile.readlines():
    count += 1
    
    if ';' in line:
      pieces = line.split(';', 1)[0].split()
    else:
      pieces = line.split()
    
    if len(pieces) == 0:
      outfile.write(line)
      continue
    
    if pieces[0].lower() == '#endif':
      if len(ifstack) == 0:
        print('unmatched ENDIF directive in ' + filename, file=sys.stderr)
        errfile.write('unmatched ENDIF directive in file ' + filename + \
                      ' at line ' + str(count) + '\n')
        sys.exit(1)
      ifstack.pop()
      outfile.write(line)
      continue

    if pieces[0].lower() == '#else':
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
    
    if pieces[0].lower() == '#ifdef':
      if pieces[1].lower() in defines:
        ifstack.append(True)
      else:
        ifstack.append(False)
      outfile.write(line)
      continue
    
    if pieces[0].lower() == '#ifndef':
      if pieces[1].lower() in defines:
        ifstack.append(False)
      else:
        ifstack.append(True)
      outfile.write(line)
      continue
    
    if pieces[0].lower() == '#if':
      ifstack.append(None)
      continue
    
    if pieces[0].lower() == '#define':
      if len(pieces) > 2:
        defines[pieces[1].lower()] = pieces[2]
      else:
        defines[pieces[1].lower()] = None
      outfile.write(line)
      continue

    if pieces[0].lower() == '#undefine':
      if pieces[1].lower() in defines:
        del defines[pieces[1].lower()]
      outfile.write(line)
      continue
    
    if pieces[0].lower() == '#include':
      if len(ifstack) > 0 and False in ifstack:
        # conditional says to not include it
        outfile.write('; PRE-PREPROCESSOR, skipping include directive due to \
                      condition stack\n')
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
      parse_file(recfile, outfile, recfn)
      recfile.close()
      outfile.write('\n')
      continue
    
    if pieces[0].lower() in ['#insert', '#section', ]:
      if len(ifstack) > 0 and False in ifstack:
        # conditional says to not compile it, so look for special preprocessor
        # directives to strip out
        outfile.write('; PRE-PREPROCESSOR, skipping special directive due to \
                      condition stack\n')
        outfile.write('; PRE-PREPROCESSOR: ' + line + '\n')
        outfile.write('; PRE-PREPROCESSOR: ' + str(ifstack) + '\n')
        continue
    
      elif pieces[0].lower() == '#insert':
        if pieces[2].lower() in sections:
          if sections[pieces[2].lower()] is None:
            outfile.write('; PRE-PREPROCESSOR, found INSERT directive after SECTION directive\n')
            sys.exit(1)
        else:
          sections[pieces[2].lower()] = []
        if len(pieces) > 3:
          priority = float(pieces[3])
        else:
          priority = 100.0
        heapq.heappush(sections[pieces[2].lower()], (priority, pieces[1]))
        outfile.write('; PRE-PREPROCESSOR, found INSERT directive\n')
        outfile.write('; PRE-PREPROCESSOR: ' + line + '\n')
        continue
      
      elif pieces[0].lower() == '#section':
        if not pieces[1].lower() in sections:
          print('WARNING: no sections for SECTION directive: ' + \
                pieces[1].lower(), file=sys.stderr)
          outfile.write('; PRE-PREPROCESSOR, WARNING, nothing found for \
                        SECTION directive: ' + pieces[1].lower() + '\n')
          outfile.write('; PRE-PREPROCESSOR: ' + line + '\n')
        else:
          outfile.write('; PRE-PREPROCESSOR, found SECTION directive\n')
          outfile.write('; PRE-PREPROCESSOR: ' + line + '\n')
          while sections[pieces[1].lower()]:
            macro = heapq.heappop(sections[pieces[1].lower()])[1]
            outfile.write('\t' + macro + '\n')
        sections[pieces[1].lower()] = None
        continue
    
    if not processor and pieces[0].lower() == 'processor':
      processor = pieces[1]
    
    outfile.write(line)
    continue
  
  infile.close()
    
    
    
# -----------------------------------------------------------------------------

try:
  infile = open(sys.argv[1], 'r')
except Exception as msg:
  print("failed to import file, error: " + str(msg))
  sys.exit(1)

if '.' in sys.argv[1]:
  basename = sys.argv[1].split('.')[0]
else:
  basename = sys.argv[1]

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

ifstack = []

parse_file(infile, outfile, sys.argv[1])

outfile.close()

# -----------------------------------------------------------------------------
# pass generated output to assembler program
if mpasm_prog:

  args = []
  args.append(mpasm_prog)
  args.append('-e' + basename + '.ERR')
  args.append('-l' + basename + '.LST')
  args.append('-o' + basename + '.o')
  if processor:
    args.append('-p' + processor)
  args.append(interim_file)
  
  proc = subprocess.Popen(args)
  
  while proc.poll() is None:
    time.sleep(0.5)
  
  if proc.poll() != 0:
    print('MPASM returned non-zero: ' + str(proc.poll()), file=sys.stderr)
    sys.exit(proc.poll())

else:
  sys.exit(0)

# -----------------------------------------------------------------------------
# pass generated output to linker program
if mplink_prog:
  
  args = []
  args.append(mplink_prog)
  if processor:
    args.append('-p' + processor)
  args.append('-w')
  args.append('-m' + basename + '.map')
  args.append('-o' + basename + '.cof')
  args.append(basename + '.o')
  
  proc = subprocess.Popen(args)
  
  while proc.poll() is None:
    time.sleep(0.5)
  
  if proc.poll() != 0:
    print('MPLINK returned non-zero: ' + str(proc.poll()), file=sys.stderr)
    sys.exit(proc.poll())


else:
  sys.exit(0)

  