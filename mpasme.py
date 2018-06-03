#!/usr/bin/env python3

'''
Microchip MPasm assembler preprocessor.


'''


import sys, heapq

print(sys.argv)  ####################

defines = {}
sections = {}

# -----------------------------------------------------------------------------

def parse_file(infile, outfile, filename):
  
  ifstack = []
  
  for line in infile.readlines():
    
    pieces = line.split()
    
    if len(pieces) == 0:
      outfile.write(line)
      continue
    
    if pieces[0].lower() == '#endif':
      if len(ifstack) == 0:
        print('unmatched ENDIF declaration', file=sys.stderr)
        sys.exit(1)
      ifstack.pop()
      outfile.write(line)
      print('ENDIF declaration', file=sys.stderr) ########################
      continue

    if pieces[0].lower() == '#else':
      if len(ifstack) == 0:
        print('unmatched ELSE declaration', file=sys.stderr)
        sys.exit(1)
      index = len(ifstack) - 1
      print('ELSE declaration', file=sys.stderr) ########################
      if ifstack[index] is True:
        ifstack[index] = False
      elif ifstack[index] is False:
        ifstack[index] = True
    
    if pieces[0].lower() == '#ifdef':
      if pieces[1].lower() in defines:
        ifstack.append(True)
        print('IFDEF True declaration: ' + line.strip(), \
              file=sys.stderr) ########################
      else:
        ifstack.append(False)
        print('IFDEF False declaration: ' + line.strip(), \
              file=sys.stderr) ########################
      outfile.write(line)
      continue
    
    if pieces[0].lower() == '#ifndef':
      if pieces[1].lower() in defines:
        ifstack.append(False)
        print('IFNDEF False declaration: ' + line.strip(), \
              file=sys.stderr) ########################
      else:
        ifstack.append(True)
        print('IFDEF True declaration: ' + line.strip(), \
              file=sys.stderr) ########################
    
    if pieces[0].lower() == '#if':
      ifstack.append(None)
    
    if len(ifstack) > 0 and False in ifstack:
      # conditional says to not compile it, so look for special preprocessor
      # directives to strip out
      if not pieces[0].lower() in ['#insertmacro', '#insertsection', ]:
        outfile.write(line)
      continue
    
    if pieces[0].lower() == '#define':
      if len(pieces) > 2:
        defines[pieces[1].lower()] = pieces[2]
      else:
        defines[pieces[1].lower()] = None
      outfile.write(line)
      print('dest define value for: ' + pieces[1], file=sys.stderr) ##############
      continue
    
    if pieces[0].lower() == '#insertmacro':
      if pieces[2].lower() in sections:
        if sections[pieces[2].lower()] is None:
          print('INSERTMACRO after INSERTSECTION', file=sys.stderr) ########################
          sys.exit(1)
      else:
        sections[pieces[2].lower()]= []
      if len(pieces) > 3:
        priority = float(pieces[3])
      else:
        priority = 100.0
      heapq.push(sections[pieces[2].lower()], (priority, pieces[1]))
      print('found INSERTMACRO: ' + pieces[2] + ' ' + pieces[1], \
            file=sys.stderr) ########################
      continue
    
    if pieces[0].lower() == '#insertsection':
      if not pieces[1].lower() in sections:
        print('WARNING: no sections for INSERTSECTION', file=sys.stderr)
      else:
        print('found INSERTSECTION: ' + pieces[1], \
              file=sys.stderr) ########################
        for priority, macro in heapq.heappop(pieces[1].lower()):
          outfile.write('\t' + macro + '\n')
      sections[pieces[1].lower()] = None
      continue
    
    if pieces[0].lower() == '#include':
      recfn = pieces[1]
      if recfn[:1] == '<':
        recfn = recfn[1:-1]
      print('recursing to include file: ' + recfn, file=sys.stderr) ########################
      try:
        recfile = open(recfn, 'r')
      except Exception as msg:
        print('failed to open file to recurse to: ' + recfn, file=sys.stderr)
        print('ERROR: ' + str(msg), file=sys.stderr)
        sys.exit(1)
      parse_file(recfile, outfile, recfn)
    
  infile.close()
    
    
    
# -----------------------------------------------------------------------------

try:
  infile = open(sys.argv[1], 'r')
except Exception as msg:
  print("failed to import file, error: " + str(msg))
  sys.exit(1)

try:
  outfile = open('pre_processed_file.asm', 'w')
except Exception as msg:
  print("failed to create output file, error: " + str(msg))
  sys.exit(1)


parse_file(infile, outfile, sys.argv[1])

outfile.close()

# -----------------------------------------------------------------------------
# pass output to MPasm



# -----------------------------------------------------------------------------
  