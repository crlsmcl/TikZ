from language import Rectangle,Circle,Line,AbsolutePoint,Number,Sequence
from utilities import *
from fastRender import fastRender
from render import render

import re


def reflectPoint(rx,ry,px,py):
    if rx != None: return (rx - px,py)
    if ry != None: return (px,ry - py)
    assert False
def reflect(x = None,y = None):
    def reflector(stuff):
        return stuff + [ o.reflect(x = x,y = y) for o in stuff ]
    return reflector
    
class line():
    def __init__(self, x1, y1, x2, y2, arrow = None, solid = None):
        self.arrow = arrow
        self.solid = solid
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
    def evaluate(self):
        return Line.absoluteNumbered(self.x1,
                                     self.y1,
                                     self.x2,
                                     self.y2,
                                     arrow = self.arrow,
                                     solid = self.solid)
    def reflect(self, x = None,y = None):
        (x1,y1) = reflectPoint(x,y,self.x1,self.y1)
        (x2,y2) = reflectPoint(x,y,self.x2,self.y2)
        if self.arrow:
            return line(x1,y1,x2,y2,arrow = True,solid = self.solid)
        else:
            (a,b) = min((x1,y1),(x2,y2))
            (c,d) = max((x1,y1),(x2,y2))
            return line(a,b,c,d,
                        arrow = False,
                        solid = self.solid)
        

class rectangle():
    def __init__(self, x1, y1, x2, y2):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
    def evaluate(self):
        return Rectangle.absolute(self.x1,self.y1,self.x2,self.y2)
    
    def reflect(self, x = None,y = None):
        (x1,y1) = reflectPoint(x,y,self.x1,self.y1)
        (x2,y2) = reflectPoint(x,y,self.x2,self.y2)
        return rectangle(min(x1,x2),
                         min(y1,y2),
                         max(x1,x2),
                         max(y1,y2))

class circle():
    def __init__(self,x,y):
        self.x = x
        self.y = y
    def evaluate(self):
        return Circle(center = AbsolutePoint(Number(self.x),Number(self.y)),
                      radius = Number(1))
    def reflect(self, x = None,y = None):
        return circle(*reflectPoint(x,y,self.x,self.y))

def addFeatures(fs):
    composite = {}
    for f in fs:
        for k in f:
            composite[k] = composite.get(k,0) + f[k]
    return composite

class Reflection():
    def __init__(self, command, body):
        self.command = command
        self.body = body
    def __str__(self):
        return "Reflection(%s,%s)"%(self.command,self.body)
    def convertToPython(self):
        return "%s(%s)"%(self.command, self.body.convertToPython())
    def extrapolations(self):
        for b in self.body.extrapolations():
            yield Reflection(self.command, b)
    def explode(self):
        return Reflection(self.command, self.body.explode())
    def features(self):
        return addFeatures([{'reflections':1,
                             'reflectionsX':int('x' in self.command),
                             'reflectionsY':int('y' in self.command)},
                            self.body.features()])
class Primitive():
    def __init__(self, k): self.k = k
    def __str__(self): return "Primitive(%s)"%self.k
    def convertToPython(self): return "[%s]"%self.k
    def extrapolations(self): yield self
    def explode(self):
        return self
    def features(self):
        return {'primitives':1,
                'lines':int('line' in self.k),
                'rectangle':int('rectangle' in self.k),
                'circles':int('circle' in self.k)}
class Loop():
    def __init__(self, v, bound, body, boundary = None, lowerBound = 0):
        self.v = v
        self.bound = bound
        self.body = body
        self.boundary = boundary
        self.lowerBound = lowerBound
    def __str__(self):
        if self.boundary != None:
            return "Loop(%s, %s, %s, %s, boundary = %s)"%(self.v,self.lowerBound, self.bound,self.body,self.boundary)
        return "Loop(%s, %s, %s, %s)"%(self.v,self.lowerBound, self.bound,self.body)
    def convertToPython(self):
        body = self.body.convertToPython()
        if self.boundary != None:
            body += " + ((%s) if %s > %s else %s)"%(self.boundary.convertToPython(),
                                                    self.v,
                                                    self.lowerBound,
                                                    '[]')
            
        return "[ _%s for %s in range(%s,%s) for _%s in (%s) ]"%(self.v,
                                                               self.v,
                                                               self.lowerBound,
                                                               self.bound,
                                                               self.v,
                                                               body)
        
    def extrapolations(self):
        for b in self.body.extrapolations():
            for boundary in ([None] if self.boundary == None else self.boundary.extrapolations()):
                for ub,lb in [(1,1),(1,0),(0,1),(0,0)]:
                    yield Loop(self.v, '%s + %d'%(self.bound,ub), b,
                               lowerBound = self.lowerBound - lb,
                               boundary = boundary)
    def explode(self):
        shrapnel = [ Loop(self.v,self.bound,bodyExpression.explode(),lowerBound = self.lowerBound)
                       for bodyExpression in self.body.items ]
        if self.boundary != None:
            shrapnel += [ Loop(self.v,self.bound,Block([]),lowerBound = self.lowerBound,
                               boundary = bodyExpression.explode())
                       for bodyExpression in self.boundary.items ]
        return Block(shrapnel)
    def features(self):
        f2 = int(str(self.bound) == '2')
        f3 = int(str(self.bound) == '3')
        f4 = int(str(self.bound) == '4')
        return addFeatures([{'loops':1,
                             '2': f2,
                             '3': f3,
                             '4': f4,
                             'boundary': int(self.boundary != None),
                             'variableLoopBound': int(f2 == 0 and f3 == 0 and f4 == 0)},
                            self.body.features(),
                            self.boundary.features() if self.boundary != None else {}])                             
                
class Block():
    def convertToSequence(self):
        return Sequence([ p.evaluate() for p in eval(self.convertToPython()) ])
    def __init__(self, items): self.items = items
    def __str__(self): return "Block([%s])"%(", ".join(map(str,self.items)))
    def convertToPython(self):
        if self.items == []: return "[]"
        return " + ".join([ x.convertToPython() for x in self.items ])
    def extrapolations(self):
        if self.items == []: yield self
        else:
            for e in self.items[0].extrapolations():
                for s in Block(self.items[1:]).extrapolations():
                    yield Block([e] + s.items)
    def explode(self):
        return Block([ x.explode() for x in self.items ])
    def features(self):
        return addFeatures([ x.features() for x in self.items ])

# return something that resembles a syntax tree, built using the above classes
def parseSketchOutput(output, environment = None, loopDepth = 0):
    commands = []
    # variable bindings introduced by the sketch: we have to resolve them
    environment = {} if environment == None else environment
    output = output.split('\n')

    def getBlock(name, startingIndex, startingDepth = 0):
        d = startingDepth

        while d > -1:
            if 'dummyStart' in output[startingIndex] and name in output[startingIndex]:
                d += 1
            elif 'dummyEnd' in output[startingIndex] and name in output[startingIndex]:
                d -= 1
            startingIndex += 1

        return startingIndex

    def getBoundary(startingIndex):
        while True:
            if 'dummyStartBoundary' in output[startingIndex]:
                return getBlock('Boundary', startingIndex + 1)
            if 'dummyStartLoop' in output[startingIndex]:
                return None
            if 'dummyEndLoop' in output[startingIndex]:
                return None
            startingIndex += 1
                

    j = 0
    while j < len(output):
        l = output[j]
        if 'void renderSpecification' in l: break

        m = re.search('validate[X|Y]\((.*), (.*)\);',l)
        if m:
            environment[m.group(2)] = m.group(1)
            j += 1
            continue

        # apply the environment
        for v in sorted(environment.keys(), key = lambda v: -len(v)):
            # if v in l:
            #     print "Replacing %s w/ %s in %s gives %s"%(v,environment[v],l,l.replace(v,environment[v]))
            l = l.replace(v,environment[v])

        
        pattern = '\(\(\(shapeIdentity == 0\) && \(cx.* == (.+)\)\) && \(cy.* == (.+)\)\)'
        m = re.search(pattern,l)
        if m:
            x = parseExpression(m.group(1))
            y = parseExpression(m.group(2))
            commands += [Primitive('circle(%s,%s)'%(x,y))]
            j += 1
            continue

        pattern = 'shapeIdentity == 1\) && \((.*) == lx1.*\)\) && \((.*) == ly1.*\)\) && \((.*) == lx2.*\)\) && \((.*) == ly2.*\)\) && \(([01]) == dashed\)\) && \(([01]) == arrow'
        m = re.search(pattern,l)
        if m:
            if False:
                print "Reading line!"
                print l
                for index in range(5): print "index",index,"\t",m.group(index),'\t',parseExpression(m.group(index))
            commands += [Primitive('line(%s,%s,%s,%s,arrow = %s,solid = %s)'%(parseExpression(m.group(1)),
                                                                              parseExpression(m.group(2)),
                                                                              parseExpression(m.group(3)),
                                                                              parseExpression(m.group(4)),
                                                                              m.group(6) == '1',
                                                                              m.group(5) == '0'))]
            j += 1
            continue
        

        pattern = '\(\(\(\(\(shapeIdentity == 2\) && \((.+) == rx1.*\)\) && \((.+) == ry1.*\)\) && \((.+) == rx2.*\)\) && \((.+) == ry2.*\)\)'
        m = re.search(pattern,l)
        if m:
            # print m,m.group(1),m.group(2),m.group(3),m.group(4)
            commands += [Primitive('rectangle(%s,%s,%s,%s)'%(parseExpression(m.group(1)),
                                                             parseExpression(m.group(2)),
                                                             parseExpression(m.group(3)),
                                                             parseExpression(m.group(4))))]
            j += 1
            continue

        pattern = 'for\(int (.*) = 0; .* < (.*); .* = .* \+ 1\)'
        m = re.search(pattern,l)
        if m and (not ('reflectionIndex' in m.group(1))):
            boundaryIndex = getBoundary(j + 1)
            if boundaryIndex != None:
                boundary = "\n".join(output[(j+1):boundaryIndex])
                boundary = parseSketchOutput(boundary, environment, loopDepth + 1)
                j = boundaryIndex
            else:
                boundary = None
            
            bodyIndex = getBlock('Loop', j+1)
            body = "\n".join(output[(j+1):bodyIndex])
            j = bodyIndex

            bound = parseExpression(m.group(2))
            body = parseSketchOutput(body, environment, loopDepth + 1)
            v = ['i','j'][loopDepth]
            commands += [Loop(v, bound, body, boundary)]
            continue

        pattern = 'dummyStartReflection\(([0-9]+), ([0-9]+)\)'
        m = re.search(pattern,l)
        if m:
            bodyIndex = getBlock('Reflection', j+1)
            body = "\n".join(output[(j+1):bodyIndex])
            j = bodyIndex
            x = int(m.group(1))
            y = int(m.group(2))
            k = 'reflect(%s = %d)'%('x' if y == 0 else 'y',
                                    max([x,y]))
            commands += [Reflection(k,
                                    parseSketchOutput(body, environment, loopDepth))]

        j += 1
            
        
    return Block(commands)

def parseExpression(e):
    try: return int(e)
    except:
        factor = re.search('([\-0-9]+) * ',e)
        if factor != None: factor = int(factor.group(1))
        offset = re.search(' \+ ([\-0-9]+)',e)
        if offset != None: offset = int(offset.group(1))
        variable = re.search('\[(\d)\]',e)
        if variable != None: variable = ['i','j'][int(variable.group(1))]

        if factor == None:
            factor = 1
        if offset == None: offset = 0
        if variable == None:
            print e
            assert False

        if factor == 0: return str(offset)

        representation = variable
        if factor != 1: representation = "%d*%s"%(factor,representation)

        if offset != 0: representation += " + %d"%offset

        return representation

        # return "%s * %s + %s"%(str(factor),
        #                        str(variable),
        #                        str(offset))


def renderEvaluation(s, exportTo = None):
    parse = evaluate(eval(s))
    x0 = min([x for l in parse.lines for x in l.usedXCoordinates()  ])
    y0 = min([y for l in parse.lines for y in l.usedYCoordinates()  ])
    x1 = max([x for l in parse.lines for x in l.usedXCoordinates()  ])
    y1 = max([y for l in parse.lines for y in l.usedYCoordinates()  ])

    render([parse.TikZ()],showImage = exportTo == None,exportTo = exportTo,canvas = (x1+1,y1+1), x0y0 = (x0 - 1,y0 - 1))

if __name__ == '__main__':
    print parseSketchOutput('''
void render (int shapeIdentity, int cx, int cy, int lx1, int ly1, int lx2, int ly2, bit dashed, bit arrow, int rx1, int ry1, int rx2, int ry2, ref bit _out)  implements renderSpecification/*tmpatQqlp.sk:205*/
{
  _out = 0;
  assume (((shapeIdentity == 0) || (shapeIdentity == 1)) || (shapeIdentity == 2)): "Assume at tmpatQqlp.sk:206"; //Assume at tmpatQqlp.sk:206
  assume (shapeIdentity != 2): "Assume at tmpatQqlp.sk:208"; //Assume at tmpatQqlp.sk:208
  assume (!(dashed)): "Assume at tmpatQqlp.sk:212"; //Assume at tmpatQqlp.sk:212
  assume (!(arrow)): "Assume at tmpatQqlp.sk:213"; //Assume at tmpatQqlp.sk:213
  int[0] environment = {};
  dummyStartLoop();
  int loop_body_cost = 0;
  bit _pac_sc_s7_s9 = 0;
  for(int j = 0; j < 3; j = j + 1)/*Canonical*/
  {
    bit _pac_sc_s23 = _pac_sc_s7_s9;
    if(!(_pac_sc_s7_s9))/*tmpatQqlp.sk:101*/
    {
      int[1] _pac_sc_s23_s25 = {0};
      push(0, environment, j, _pac_sc_s23_s25);
      int x_s31 = 0;
      validateX((3 * (_pac_sc_s23_s25[0])) + 1, x_s31);
      int y_s35 = 0;
      validateY(6, y_s35);
      bit _pac_sc_s23_s27 = 0 || (((shapeIdentity == 0) && (cx == x_s31)) && (cy == y_s35));
      int x_s31_0 = 0;
      validateX((3 * (_pac_sc_s23_s25[0])) + 1, x_s31_0);
      int y_s35_0 = 0;
      validateY(1, y_s35_0);
      _pac_sc_s23_s27 = _pac_sc_s23_s27 || (((shapeIdentity == 0) && (cx == x_s31_0)) && (cy == y_s35_0));
      int x_s31_1 = 0;
      validateX((3 * (_pac_sc_s23_s25[0])) + 1, x_s31_1);
      int y_s35_1 = 0;
      validateY((_pac_sc_s23_s25[0]) + 2, y_s35_1);
      int x2_s39 = 0;
      validateX((3 * (_pac_sc_s23_s25[0])) + 1, x2_s39);
      int y2_s43 = 0;
      validateY(5, y2_s43);
      loop_body_cost = 3;
      _pac_sc_s23_s27 = _pac_sc_s23_s27 || (((((((shapeIdentity == 1) && (x_s31_1 == lx1)) && (y_s35_1 == ly1)) && (x2_s39 == lx2)) && (y2_s43 == ly2)) && (0 == dashed)) && (0 == arrow));
      _pac_sc_s23 = _pac_sc_s23_s27;
    }
    _pac_sc_s7_s9 = _pac_sc_s23;
  }
  assert (loop_body_cost != 0); //Assert at tmpatQqlp.sk:103 (6533586931555877886)
  dummyEndLoop();
  _out = _pac_sc_s7_s9;
  minimize(loop_body_cost + 1)
''')
