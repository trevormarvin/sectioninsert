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
  
  for line in infile.readlines():
    
    if ';' in line:
      pieces = line.split(';', 1)[0].split()
    else:
      pieces = line.split()
    
    if len(pieces) == 0:
      outfile.write(line)
      continue
    
    if pieces[0].lower() == '#endif':
      if len(ifstack) == 0:
        print('unmatched ENDIF declaration in ' + filename, file=sys.stderr)
        sys.exit(1)
      ifstack.pop()
      outfile.write(line)
      print('ENDIF declaration', file=sys.stderr) ########################
      continue

    if pieces[0].lower() == '#else':
      if len(ifstack) == 0:
        print('unmatched ELSE declaration in ' + filename, file=sys.stderr)
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
      print('dest define value for: ' + pieces[1], file=sys.stderr) ##############
      continue

    if pieces[0].lower() == '#undefine':
      if pieces[1].lower() in defines:
        del defines[pieces[1].lower()]
        print('undefine value for: ' + pieces[1], file=sys.stderr) ##############
      else:
        print('attempted undefine on undefined value: ' + pieces[1], file=sys.stderr) ##############
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
        print('skipping expanding include file: ' + recfn, file=sys.stderr) ########################
        outfile.write('; PRE-PREPROCESSOR, skipping expanding included file: ' \
                      + recfn + '\n')
        outfile.write(line)
        continue
      print('recursing to include file: ' + recfn, file=sys.stderr) ########################
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
            print('INSERT after SECTION', file=sys.stderr) ########################
            sys.exit(1)
        else:
          sections[pieces[2].lower()] = []
        if len(pieces) > 3:
          priority = float(pieces[3])
        else:
          priority = 100.0
        heapq.push(sections[pieces[2].lower()], (priority, pieces[1]))
        outfile.write('; PRE-PREPROCESSOR, found INSERT directive\n')
        outfile.write('; PRE-PREPROCESSOR: ' + line + '\n')
        print('found INSERT: ' + pieces[2] + ' ' + pieces[1], \
              file=sys.stderr) ########################
        continue
      
      elif pieces[0].lower() == '#section':
        if not pieces[1].lower() in sections:
          print('WARNING: no sections for SECTION directive', file=sys.stderr)
          outfile.write('; PRE-PREPROCESSOR, WARNING, nothing found for \
                        SECTION directive\n')
          outfile.write('; PRE-PREPROCESSOR: ' + line + '\n')
        else:
          outfile.write('; PRE-PREPROCESSOR, found SECTION directive\n')
          outfile.write('; PRE-PREPROCESSOR: ' + line + '\n')
          print('found SECTION directive: ' + pieces[1], \
                file=sys.stderr) ########################
          for priority, macro in heapq.heappop(pieces[1].lower()):
            outfile.write('\t' + macro + '\n')
        sections[pieces[1].lower()] = None
        continue
    
    outfile.write(line)
    continue
  
  infile.close()
    
    
    
# -----------------------------------------------------------------------------

try:
  infile = open(sys.argv[1], 'r')
except Exception as msg:
  print("failed to import file, error: " + str(msg))
  sys.exit(1)

try:
  outfile = open('_pre_processed_file.asm', 'w')
except Exception as msg:
  print("failed to create output file, error: " + str(msg))
  sys.exit(1)

ifstack = []

parse_file(infile, outfile, sys.argv[1])

outfile.close()

print('DEBUG, defines: ' + str(defines), \
      file=sys.stderr) ########################

# -----------------------------------------------------------------------------
# pass generated output to assembler program

####### DO STUFF HERE

# -----------------------------------------------------------------------------
  