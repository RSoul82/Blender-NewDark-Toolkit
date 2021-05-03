# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# <pep8 compliant>

# Script copyright (C) Tom N Harris
# Contributors: Bob Holcomb, Richard L?rk?ng, Damien McGinnes, Campbell Barton, Mario Lapin, Dominique Lorre

import os
import time

import bpy
import mathutils
import re


if os.name == 'nt':
    convert_exe = '""' + os.path.split(__file__)[0] + os.path.sep + 'convert.exe" "{}" "{}""'
else:
    convert_exe = 'convert "{}" "{}"'


######################################################
# Data Structures
######################################################

TOKEN = re.compile(r'\s*('
                   r'(?:-?\d+\.\d*(?:[Ee][+-]?\d+)?)|'
                   r'(?:-?\.\d+(?:[Ee][+-]?\d+)?)|'
                   r'(?:-?\d+(?:[Ee][+-]?\d+)?)|'
                   r'\w+|'
                   r'\S)', re.ASCII)


######################################################
# IMPORT
######################################################


class ParseError(Exception):

    __slots__ = ("args","str","line","column")

    def __init__(self, str, line = 0, column = 0):
        self.str = str
        self.line = line
        self.column = column
        self.args = (str,line,column)

    def __str__(self):
        if self.line and self.column:
            return "{line}:{column}: {str}".format_map(self)
        elif self.line:
            return "{line}: {str}".format_map(self)
        else:
            return "{str}".format_map(self)

    def __repr__(self):
        return "ParseError"+repr(self.args)


class Tokenizer(object):

    __slots__ = ("name", "line", "column", "tokenizer", "next_token")

    def __init__(self, filepath):
        self.name = os.path.basename(filepath)
        file = open(filepath, encoding='ascii')
        self.tokenizer = self.tokenize(file)
        self.next_token = None

    def __iter__(self):
        return self

    def __next__(self):
        token = self.get_next()
        if not token:
            raise StopIteration
        return token

    def tokenize(self, file):
        self.line = 0
        self.column = 0
        seek = None
        collect = ""

        # Scan the lines of the file
        for line in file.readlines():
            self.line += 1
            self.column = 1
            pos = 0
            match = None
            while seek:
                # continue multi-line seek
                found = line.find(seek, pos)
                if found == -1:
                    collect = collect + "\n" + line
                    break
                token = collect + "\n" + line[pos:found]
                pos = found     # the next token is the seek key
                collect = ""
                previous = seek
                while seek == previous:
                    seek = (yield token)
                    self.column = pos + 1
                    token = ""
            else:
                # Skip whitespace, find a number, word, or single character
                match = TOKEN.match(line, pos)

            # When seeking, the match should be None,
            # that will skip this loop. If not seeking,
            # collect should be empty
            while match:
                token = match.group(1)
                pos = match.end(1)

                # The token is first from the match,
                # but also from the seek that occurs inside this loop
                while token:
                    seek = (yield token)
                    self.column = pos + 1
                    if seek:
                        found = line.find(seek, pos)
                        if found == -1:
                            # seek continues to the next line,
                            # clear the match and jump out of this loop
                            collect = line[pos:]
                            match = None
                            break

                        # seek on this line
                        token = line[pos:found]
                        pos = found     # next token is the seek key
                    else:
                        # not seeking
                        token = None
                else:
                    # not seeking
                    match = TOKEN.match(line, pos)
        return

    def get_next(self):
        try:
            if self.next_token:
                token, self.next_token = self.next_token, None
            else:
                token = next(self.tokenizer)
            return token
        except StopIteration:
            return None

    def expect(self, token):
        tok = self.get_next()
        if isinstance(token, str) or token is None:
            if tok != token:
                raise ParseError(repr(token)+" expected, got "+
                                repr(tok)+" instead", self.line, self.column)
        else:
            if tok not in token:
                raise ParseError("unexpected "+repr(tok),
                                self.line, self.column)
        return tok

    def skip(self, token, expect=True):
        span = None
        try:
            span = self.tokenizer.send(token)
            if expect:
                self.expect(token)
        except StopIteration:
            if expect:
                raise ParseError(repr(token)+" expected",
                                self.line, self.column)
        return span

    def next(self):
        return self.get_next()

    def next_and_check(self, token):
        tok = self.get_next()
        self.expect(token)
        return tok

    def lookahead(self):
        if self.next_token:
            return self.next_token
        try:
            token = next(self.tokenizer)
            self.next_token = token
            return token
        except StopIteration:
            return None


def parse_E(filepath):
    tokenizer = Tokenizer(filepath)
    root = { 'MATERIALS':[], 'OBJECTS':[] }
    current = None

    def do_string():
        nonlocal tokenizer

        tokenizer.expect('"')
        return tokenizer.skip('"')

    def do_comment():
        nonlocal tokenizer

        tokenizer.expect('{')
        tokenizer.skip('}')

    def do_materials():
        nonlocal tokenizer, root, current

        tokenizer.expect('{')
        try:
            endbrace = tokenizer.lookahead()
            while endbrace and endbrace != '}':
                num = int(tokenizer.next_and_check(','))
                if num < 1:
                    raise ParseError("bad material index",
                                    tokenizer.line, tokenizer.column)
                material = { 'NUM':num }
                material['NAME'] = None
                if tokenizer.lookahead() == ',':
                    tokenizer.next()
                else:
                    material['NAME'] = do_string()
                    tokenizer.expect(',')
                material['SHADING'] = "FLAT"
                if tokenizer.lookahead() == ',':
                    tokenizer.next()
                else:
                    material['SHADING'] = tokenizer.expect({'FLAT',
                                                            'GOURAUD',
                                                            'PHONG',
                                                            'METAL'})
                    tokenizer.expect(',')
                tex = tokenizer.expect({'RGB','TMAP'})
                if tex == 'RGB':
                    r = int(tokenizer.next_and_check(','))
                    g = int(tokenizer.next_and_check(','))
                    b = int(tokenizer.next())
                    material['RGB'] = (r,g,b)
                else:   # TMAP
                    material['TMAP'] = do_string()
                    tokenizer.expect(',')
                    material['INTENSITY'] = int(tokenizer.next())
                endline = tokenizer.lookahead()
                while endline and endline != ';':
                    tokenizer.expect(',')
                    token = tokenizer.expect(('TRANSP',
                                              'ILLUM',
                                              'DBL',
                                              'WIRE',
                                              ';'))
                    if token == 'TRANSP':
                        material['TRANSP'] = int(tokenizer.next())
                    elif token == 'ILLUM':
                        material['ILLUM'] = int(tokenizer.next())
                    elif token == 'DBL':
                        material['DBL'] = True
                    elif token == 'WIRE':
                        material['WIRE'] = True
                    endline = tokenizer.lookahead()

                tokenizer.expect(';')

                #if num > len(root['MATERIALS']):
                #    root['MATERIALS'].extend((None for x in range(num - len(root['MATERIALS']))))
                root['MATERIALS'].append(material)

                endbrace = tokenizer.lookahead()

        except ValueError as exc:
            raise ParseError("bad number",
                            tokenizer.line, tokenizer.column) from exc

        tokenizer.expect('}')

    def do_begin():
        nonlocal tokenizer, root, current
        if current:
            if not current['POINTS']:
                raise ParseError("object "+current['NAME']+" has no points")
            if None in current['FACES']:
                raise ParseError("object "+current['NAME']+
                                " has non-consecutive parts")
            root['OBJECTS'].append(current)

        tokenizer.expect('"')
        name = tokenizer.skip('"')
        current = { 'NAME':name, 'POINTS':[], 'FACES':[] }

    def do_end():
        nonlocal tokenizer, root, current

        if current:
            if not current['POINTS']:
                raise ParseError("object "+current['NAME']+" has no points")
            for face in current['FACES']:
                if not face:
                    raise ParseError("object "+current['NAME']+
                                    " has non-consecutive parts")
            root['OBJECTS'].append(current)

        current = None

        tokenizer.expect(None)

    def do_points():
        nonlocal tokenizer, current

        if current is None:
            raise ParseError("POINTS before BEGIN", tokenizer.line)

        tokenizer.expect('{')
        try:
            endbrace = tokenizer.lookahead()
            while endbrace and endbrace != '}':
                x = float(tokenizer.next_and_check(','))
                y = float(tokenizer.next_and_check(','))
                z = float(tokenizer.next_and_check(';'))
                current['POINTS'].append((x,y,z))
                endbrace = tokenizer.lookahead()

        except ValueError as exc:
            raise ParseError("bad number",
                            tokenizer.line, tokenizer.column) from exc
        tokenizer.expect('}')

    def do_parts():
        nonlocal tokenizer, root, current

        if current is None:
            raise ParseError("PARTS before BEGIN", tokenizer.line)

        tokenizer.expect('{')
        try:
            endbrace = tokenizer.lookahead()
            while endbrace and endbrace != '}':
                face = {}
                flags = int(tokenizer.next_and_check(','))
                #if flags != 0 and flags != 4:
                #    raise ParseError("unknown part flag "+str(num), tokenizer.line)
                if flags != 0:
                    face['FLAGS'] = flags
                face['VISIBILITY'] = tokenizer.next_and_check(',')
                num = int(tokenizer.next_and_check(','))
                if num < 0:
                    raise ParseError("bad part index",
                                    tokenizer.line, tokenizer.column)

                mat = int(tokenizer.next_and_check(','), 16) & 0xFF
                if (mat < 1 or mat > len(root['MATERIALS'])
                or not root['MATERIALS'][mat-1]):
                    raise ParseError("bad material index",
                                    tokenizer.line, tokenizer.column)
                face['MATERIAL'] = mat - 1

                vert = []
                tokenizer.expect('(')
                paren = tokenizer.lookahead()
                while paren and paren != ')':
                    v = int(tokenizer.next())
                    if v < 0 or v >= len(current['POINTS']):
                        raise ParseError("bad vertex",
                                        tokenizer.line, tokenizer.column)
                    vert.append(v)
                    paren = tokenizer.expect((',',')'))

                if len(vert) < 3:
                    raise ParseError("expected number",
                                    tokenizer.line, tokenizer.column)

                face['VERTICES'] = tuple(vert)

                tokenizer.expect(';')

                if num >= len(current['FACES']):
                    current['FACES'].extend(
                                    (None for x in
                                    range(num + 1 - len(current['FACES']))))
                current['FACES'][num] = face

                endbrace = tokenizer.lookahead()

        except ValueError as exc:
            raise ParseError("bad number",
                            tokenizer.line, tokenizer.column) from exc

        tokenizer.expect('}')

    def do_partmappings():
        nonlocal tokenizer, current

        if current is None:
            raise ParseError("PART_MAPPINGS before BEGIN", tokenizer.line)

        tokenizer.expect('{')
        try:
            endbrace = tokenizer.lookahead()
            while endbrace and endbrace != '}':
                num = int(tokenizer.next())
                if num < 0 or num >= len(current['FACES']):
                    raise ParseError("bad part index",
                                    tokenizer.line, tokenizer.column)

                face = current['FACES'][num]
                uvmap = [None for n in range(len(face['VERTICES']))]
                for n in range(len(face['VERTICES'])):
                    tokenizer.expect(',')
                    tokenizer.expect('(')
                    uvmap[n] = (float(tokenizer.next_and_check(',')),
                                float(tokenizer.next_and_check(')')))

                tokenizer.expect(';')

                face['UV'] = tuple(uvmap)

                endbrace = tokenizer.lookahead()

        except ValueError as exc:
            raise ParseError("bad number",
                            tokenizer.line, tokenizer.column) from exc

        tokenizer.expect('}')

    blocks = {None:None,
             'BEGIN':do_begin,
             'POINTS':do_points,
             'PARTS':do_parts,
             'PART_MAPPINGS':do_partmappings,
             'MATERIALS':do_materials,
             'COMMENT':do_comment,
             'END':do_end
             }
    while True:
        block = tokenizer.expect(blocks.keys())

        if block is None:
            raise ParseError("END expected", tokenizer.line, tokenizer.column)

        blocks[block]()

        if block == 'END':
            break

    return root

def add_texture_to_material(image, texture, material, mapto):
    #print('assigning %s to %s' % (texture, material))

    if mapto not in {"COLOR", "SPECULARITY", "ALPHA", "NORMAL"}:
        print('/tError:  Cannot map to "%s"\n\tassuming diffuse color. modify material "%s" later.' % (mapto, material.name))
        mapto = "COLOR"

    if image:
        texture.image = image

    mtex = material.texture_slots.add()
    mtex.texture = texture
    mtex.texture_coords = 'UV'
    mtex.use_map_color_diffuse = False

    if mapto == 'COLOR':
        mtex.use_map_color_diffuse = True
    elif mapto == 'SPECULARITY':
        mtex.use_map_specular = True
    elif mapto == 'ALPHA':
        mtex.use_map_alpha = True
    elif mapto == 'NORMAL':
        mtex.use_map_normal = True


def convert_image_format(filepath):
    print("convert_image_format: (%s)"%(filepath,))
    fileroot, fileext = os.path.splitext(filepath)
    fileext = fileext.lower()
    if fileext == '.gif' or fileext == '.pcx':
        convpath = fileroot + '.png'
        if os.path.isfile(filepath) and not os.path.isfile(convpath):
            os.system(convert_exe.format(filepath, convpath))
        return convpath
    return filepath

#Ensures a path is absolute rather than relative
def pathToAbs(pathToSet):
    if pathToSet.startswith('..'):
        raise ValueError("Refusing to operate on path '{0}'".format(pathToSet))
    elif pathToSet != '':
        return os.path.abspath(bpy.path.abspath(os.path.expanduser(pathToSet)))
    else:
        return ''

def load_image_recursive(texName, dirname, use_recursive=False):
    from bpy_extras.image_utils import load_image 
    #see if the filename ends with an extension, i.e. length - 4 is a .
    if texName[len(texName)-4] == ".":
        texName = texName[:-4]
    
    extensions = [".dds", ".png", ".tga", ".bmp", ".gif", ".pcx", ".jpg"]
    
    for ext in extensions:        
        filepath = texName + ext
        #assign texture to material
        img = load_image(filepath, dirname, recursive=use_recursive, convert_callback=convert_image_format, check_existing=True)
        
        if img:
            return img #stops this loop/method

        #if not found in local subdirs, look in the user's user preferences textures dir (and subdirs)
        filename = os.path.basename(filepath) #filename only
        userPrefTexDir = bpy.context.preferences.filepaths.texture_directory #user preferences textures directory
        if userPrefTexDir not in ('', '//'):
            from os.path import join, isfile
            userTexs = [] #include root dir
            userTexs.append(userPrefTexDir)#add all files and subdirs
            for texDirentry in os.listdir(userPrefTexDir):
                userTexs.append(texDirentry)
                
            for texDirentry in userTexs:
                filepath = join(userPrefTexDir, texDirentry, filename)
                if isfile(filepath):
                    img = load_image(filepath, None, convert_callback=convert_image_format)
                    if img:
                        return img         
    return None #if all else fails

#Get the index of the first existing image slot whose filepath matches the image to be loaded. -1 if image not already loaded.
def getTexIndex(texturePath):
    index = -1
    for img in range(len(bpy.data.images)):
        if bpy.data.images[img].filepath == texturePath.strip():
            index = img
            break
    return index

#True if material has an image texture
def has_texture(material):
    mNodes = material.node_tree.nodes
    matOutputNode = mNodes["Material Output"]
    shaderNode = matOutputNode.inputs[0].links[0].from_node
    try:
        inputNode = shaderNode.inputs[0].links[0].from_node
        return True
    except:
        return False

#Scans a material's nodes and follows the links to get the current texture.
def get_diffuse_texture(material):
    mNodes = material.node_tree.nodes

    #get the material output node which all materials should have
    matOutputNode = mNodes.get("Material Output")

    #get whatever shader is the surface input to the material node - likely to be Diffuse BSDF or Principled BSDF
    shaderNode = matOutputNode.inputs[0].links[0].from_node

    #get the image texture that links to the shader node
    try:
        inputNode = shaderNode.inputs[0].links[0].from_node
        return inputNode.image.name

    except:
        return None

#remove all data bloks - allows things to be loaded cleanly
def removeAll():
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)

    for block in bpy.data.materials:
        if block.users == 0:
            bpy.data.materials.remove(block)

    for block in bpy.data.textures:
        if block.users == 0:
            bpy.data.textures.remove(block)

    for block in bpy.data.images:
        if block.users == 0:
            bpy.data.images.remove(block)

def axleCheck(verts):
    edges = []
    if len(verts) == 2:
        edges.append((0,1))
    return edges

def load(operator,
         context,
         filepath="",
         use_image_search=False,
         global_matrix=None,
         ):

    removeAll()
    print("importing E: %r..." % (filepath), end="")

    if bpy.ops.object.select_all.poll():
        bpy.ops.object.select_all(action='DESELECT')

    time1 = time.clock()
#   time1 = Blender.sys.time()

    try:
        efile = parse_E(filepath)
    except ParseError:
        print('\tFatal Error:  Not a valid E file: %r' % filepath)
        return {'CANCELLED'}

    importedObjects = []  # Fill this list with objects
    importedMaterials = []
    importedTextures = {}

    dirname = os.path.dirname(filepath)
    scn = context.scene

    for mat in efile['MATERIALS']:
        mName = mat['NAME'].rstrip()
        if mName not in bpy.data.materials:
            bmat = bpy.data.materials.new(mName)
            bmat.use_nodes = True
            mNodes = bmat.node_tree.nodes
            
            #delete principled shader as it's not needed for dark enigne objects
            mNodes.remove(mNodes.get('Principled BSDF'))
            
            #create diffuse shader
            shaderNode = mNodes.new(type='ShaderNodeBsdfDiffuse')
            #get the material output node which all materials should have
            matOutputNode = mNodes.get("Material Output")
            
            #for presentation only
            shaderNode.location = matOutputNode.location.x - shaderNode.width -100, matOutputNode.location.y
            
            #create link from shader to output
            links = mNodes.data.links
            links.new(shaderNode.outputs[0], matOutputNode.inputs[0])
            
            #create texture or RGB input
            if 'RGB' in mat:
                col = [co / 255 for co in mat['RGB']]
                shaderNode.inputs[0].default_value = (col[0],col[1],col[2],255)
            if 'TMAP' in mat:
                print("Loading image "+mat['TMAP']+" from "+dirname+"\n")
                img = load_image_recursive(mat['TMAP'], dirname, use_image_search)
                texture = bpy.data.textures.new(mat['TMAP'], type='IMAGE')
                if img:
                    texture.image = img
               
                if mNodes.find("Image Texture") == -1:
                    #add texture node to base color input
                    mNodes.new("ShaderNodeTexImage")
                texNode = mNodes.get("Image Texture")
                texNode.image = img # assign the found image to the texture
                
                #for presentation only
                texNode.location = shaderNode.location.x - texNode.width - 100, shaderNode.location.y
                
                #create link from texture node to shader node
                links = bmat.node_tree.links
                link = links.new(texNode.outputs[0], shaderNode.inputs[0])

            bmat.shader = mat['SHADING']
            bmat.transp = mat['TRANSP']
            bmat.illum = mat['ILLUM']
            if 'DBL' in mat:
                bmat.dbl = True
            else:
                bmat.use_backface_culling = True
        else:
            bmat = bpy.data.materials[mName]
        
        #lists materials associated with this object, which were all either created for this object or already existed.
        importedMaterials.append(bmat.name)
    
    for obj in efile['OBJECTS']:
        obName = obj['NAME']
        verts = obj['POINTS']
        edges = [] # will be empty if obj has polys, or 1 edge if obj is axle
        faces = [f['VERTICES'] for f in obj['FACES']]
        
        try:
            uv_data = [uv for f in obj['FACES'] for uv in f['UV']]
        except:
            uv_data = None
        
        newObj = bpy.data.objects.new(obName, bpy.data.meshes.new(obName))
        
        #add edge between two points of axle object, or leave empty and use faces instead
        edges = axleCheck(verts)
        
        newObj.data.from_pydata(verts, edges, faces)
        newObj.data.validate()
        
        for source, target in zip(obj['FACES'], newObj.data.polygons):
            efileMatID = source['MATERIAL'] #0 indexed material ID assigned to each face in
            importedName = importedMaterials[efileMatID]
            if importedName not in newObj.data.materials:
                newObj.data.materials.append(bpy.data.materials[importedName])
            
            target.material_index = newObj.data.materials.find(importedName)

        uv_map = newObj.data.uv_layers.new(do_init=False)
        if uv_data is not None:
            for loop, uv in zip(uv_map.data, uv_data):
                loop.uv = uv
        
        if not bpy.data.collections:
            bpy.data.collections.new("Collection 1")
        bpy.data.collections[0].objects.link(newObj)

    # Select all new objects.
    print(" done in %.4f sec." % (time.clock() - time1))

    return {'FINISHED'}
