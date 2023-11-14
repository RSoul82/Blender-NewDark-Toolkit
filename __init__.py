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

bl_info = {
    'name': 'Blender NewDark Toolkit',
    'author': 'Tom N Harris, 2.80/2.9x/3.x update by Robin Collier, including adaptions from the Dark Exporter 2 by Elendir',
    'version': (1, 5, 3),
    'blender': (2, 92, 0),
    'location': 'File > Import-Export',
    'description': 'Import E files, Export Bin, including textures',
#    'wiki_url': '',
#    'tracker_url': '',
#    'support': '',
    'category': 'Import-Export'}

# To support reload properly, try to access a package var, if it's there, reload everything
if 'bpy' in locals():
    import importlib
    if 'import_e' in locals():
        importlib.reload(import_e)
    if 'export_bin' in locals():
        importlib.reload(export_bin)


import bpy
import os
import json
from bpy.props import StringProperty, FloatProperty, BoolProperty, EnumProperty, IntProperty
from bpy_extras.io_utils import ImportHelper, ExportHelper, axis_conversion

default_config = {
'ai_mesh': False,
'bsp_optimization': 0,
'centering': True,
'selection_only': False,
'smooth_angle': 89,
'game_dirs': 'C:\\Games\\Thief2',
'bsp_meshbld_dir': 'C:\\Games\\Thief2\\Tools\\3dstobin\\3ds\\Workshop',
'autodel': False,
'bin_copy': True,
'tex_copy': 1
}

config_filename = 'Bin_Export.cfg'
config_path = bpy.utils.user_resource('CONFIG', path='scripts', create=True)
config_filepath = os.path.join(config_path, config_filename)

def load_config():
    config_file = open(config_filepath, 'r')
    config_from_file = json.load(config_file)
    config_file.close()
    return config_from_file

try:
    config_file = open(config_filepath, 'r')
    config_from_file = json.load(config_file)
    config_file.close()
except IOError:
    config_file = open(config_filepath, 'w')
    json.dump(default_config, config_file, indent=4, sort_keys=True)
    config_file.close()
    load_config()
    
#Try to get a value from a config file. Return ... if key not founnd.
def tryConfig(key, config_from_file):
    try:
        return config_from_file[key]
    except:
        config_file.close()
        config_from_file[key] = default_config[key] #add missing key with default value
        config_update = open(config_filepath, 'w')
        json.dump(config_from_file, config_update, indent = 4, sort_keys = True)
        config_update.close()
        load_config()
        return config_from_file[key]

class ImportE(bpy.types.Operator, ImportHelper):
    '''Import from E file format (.e)'''
    bl_idname = 'import_scene.efile'
    bl_label = 'Import E file'

    filename_ext = '.e'
    filter_glob: StringProperty(default='*.e', options={'HIDDEN'})

    use_image_search: BoolProperty(name='Texture Search', description='Search subdirectories for any associated textures. Also searches the textures dir set in User Preferences.  (Warning, may be slow)', default=False)

    axis_forward: EnumProperty(
            name='Forward',
            items=(('X', 'X Forward', ''),
                   ('Y', 'Y Forward', ''),
                   ('Z', 'Z Forward', ''),
                   ('-X', '-X Forward', ''),
                   ('-Y', '-Y Forward', ''),
                   ('-Z', '-Z Forward', ''),
                   ),
            default='Y',
            )

    axis_up: EnumProperty(
            name='Up',
            items=(('X', 'X Up', ''),
                   ('Y', 'Y Up', ''),
                   ('Z', 'Z Up', ''),
                   ('-X', '-X Up', ''),
                   ('-Y', '-Y Up', ''),
                   ('-Z', '-Z Up', ''),
                   ),
            default='Z',
            )

    def execute(self, context):
        from . import import_e

        keywords = self.as_keywords(ignore=('axis_forward', 'axis_up', 'filter_glob'))

        global_matrix = axis_conversion(from_forward=self.axis_forward, from_up=self.axis_up).to_4x4()
        keywords['global_matrix'] = global_matrix

        return import_e.load(self, context, **keywords)

class ExportBin(bpy.types.Operator, ExportHelper):
    '''Export to Bin file format (.bin)'''
    bl_idname = 'export_scene.binfile'
    bl_label = 'Export Bin file'
    filename_ext = '.bin'
    filter_glob: StringProperty(default='*.bin', options={'HIDDEN'})
    bl_options = {'PRESET'}

    use_selection: BoolProperty(name='Selection Only', description='Export selected objects only', default=False)
    centering: BoolProperty(name='Center object', default=tryConfig('centering', config_from_file), 
    description='Center your object near its centroid')
    apply_modifiers: BoolProperty(name='Apply Modifiers', description='Apply modifiers to exported object.', default = True)
    smooth_angle: IntProperty(name='Smooth Angle', min=0, max=360, step=1, description='Max angle between faces that should be smoothly shaded. Default: 120. Only applies to Phong/Gouraud materials', default=tryConfig('smooth_angle', config_from_file))
    bsp_optimization: IntProperty(name='BSP Optimization', min=0, max=3, step=1, description='BSP Optimization levels (0 recommended)', default=0)
    use_coplanar_limit: BoolProperty(name='Use Coplanar Limit', description='Disable this if you can see errors in your object\'s shape', default = True)
    coplanar_limit: FloatProperty(name='Coplanar Limit', description='Change this if you get small gaps in the model or flattened faces', default = 1.0)
    
    bsp_dir: StringProperty(default=tryConfig('bsp_meshbld_dir', config_from_file), name='BSP/MeshBld Dir', description='Folder containing BSP.exe and/or MeshBld.exe')
    
    #generate game dirs list
    gDirsString = tryConfig('game_dirs', config_from_file)
    split = gDirsString.split(';')
    enum_dirs = []
    game_dirs = []
    for i in range(0, len(split)):
        enum_dirs.append((str(i), split[i].strip(), ''))
        game_dirs.append(split[i].strip())
    
    game_dir_ID: EnumProperty(name='Game Dir', items = enum_dirs, description='Folder containing Thief/Thief2.exe, Dromed.exe, Shock2.exe etc')
    bin_copy: BoolProperty(name='Bin Copy', default=tryConfig('bin_copy', config_from_file),
    description='Copy model to obj subfolder')
    autodel: BoolProperty(name='Delete temp files', default=tryConfig('autodel', config_from_file),
    description='Delete local temporary files.')
    tex_copy: EnumProperty(name='Copy Textures', items=(('0', 'Never', ''), ('1', 'Only if not present', ''), ('2', 'Always', '')), default='1',
    description='Copy textures to obj\\txt16. Default = Only when texture isn\'t already in txt16')
    ai_mesh: BoolProperty(name='AI Mesh', description='Use MeshBld and a .cal file (see below) to export to the mesh folder', default=False)
    mesh_type: EnumProperty(
            name='MeshType',
            items=(('apparition', 'Apparation', ''),
                   ('arm', 'Arm', ''),
                   ('bowarm', 'Bow Arm', ''),
                   ('bugbeast', 'Bug Beast', ''),
                   ('burrick', 'Burrick', ''),
                   ('constantine', 'Constantine', ''),
                   ('crayman', 'Crayman', ''),
                   ('deadburrick', 'Dead Burrick', ''),
                   ('droid', 'Droid', ''),
                   ('frog', 'Frog', ''),
                   ('humanoid', 'Humanoid', ''),
                   ('rope', 'Rope', ''),
                   ('simple', 'Simple', ''),
                   ('spider', 'Spider', ''),
                   ('sweel', 'Sweel', ''),
                   ),
            default='humanoid',
            )
    
    axis_forward: EnumProperty(
            name='Forward',
            items=(('X', 'X Forward', ''),
                   ('Y', 'Y Forward', ''),
                   ('Z', 'Z Forward', ''),
                   ('-X', '-X Forward', ''),
                   ('-Y', '-Y Forward', ''),
                   ('-Z', '-Z Forward', ''),
                   ),
            default='Y',
            )

    axis_up: EnumProperty(
            name='Up',
            items=(('X', 'X Up', ''),
                   ('Y', 'Y Up', ''),
                   ('Z', 'Z Up', ''),
                   ('-X', '-X Up', ''),
                   ('-Y', '-Y Up', ''),
                   ('-Z', '-Z Up', ''),
                   ),
            default='Z',
            )
    
    def execute(self, context):
        from . import export_bin

        keywords = self.as_keywords(ignore=('axis_forward', 'axis_up', 'filter_glob', 'check_existing'))
        global_matrix = axis_conversion(to_forward=self.axis_forward, to_up=self.axis_up).to_4x4()
        keywords['global_matrix'] = global_matrix
        keywords['game_dirs'] = self.game_dirs #this is needed to get pass the array items to the export class
        keywords['extra_bsp_params'] = context.scene.bspParams

        return export_bin.save(self, context, **keywords)

def get_active_mat(self, context):
    return context.active_object.active_material

class MaterialPropertiesPanel(bpy.types.Panel):
    bl_idname = 'DE_MATPANEL_PT_dark_engine_exporter'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'material'
    bl_label = 'Dark Engine Materials (NewDark Toolkit)'
    
    def draw(self, context):
        activeMat = get_active_mat(self, context)
        layout = self.layout
        layout.row().prop(activeMat, 'shader')
        layout.row().prop(activeMat, 'transp')
        layout.row().prop(activeMat, 'illum')
        layout.row().prop(activeMat, 'dbl')
        layout.row().prop(activeMat, 'nocopy')
        layout.row().separator()
        layout.row().operator('material.import_from_custom', icon = 'MATERIAL')

class ImportMaterialFromCustomProps(bpy.types.Operator):
    bl_idname = 'material.import_from_custom'
    bl_label = 'Import Materials from Custom Properties.'
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        activeMat = get_active_mat(self, context)
        if 'SHADER' in activeMat:
            activeMat.shader = activeMat['SHADER']
        if 'TRANSP' in activeMat:
            activeMat.transp = activeMat['TRANSP']
        if 'ILLUM' in activeMat:
            activeMat.illum = activeMat['ILLUM']
        if 'DBL' in activeMat:
            if activeMat['DBL'] == 1.0:
                activeMat.dbl = True;
        if 'NoCopy' in activeMat:
            if activeMat['NoCopy'] == 1.0:
                activeMat.nocopy = True;
        return {'FINISHED'}

class BSPExportParams(bpy.types.Panel):
    bl_idname = 'DE_BSPPANEL_PT_dark_engine_exporter'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'object'
    bl_label = 'BSP Export Params (NewDark Toolkit)'

    def draw(self, context):
        layout = self.layout
        layout.row().label(text='Additional BSP Params:')
        layout.row().prop(context.scene, 'bspParams')
        layout.row().label(text='NOTE: Incorrect/duplicate params may cause conversion errors.')
        layout.row().operator('file.open_config', icon = 'SETTINGS')
        
class OpenConfigFile(bpy.types.Operator):
    bl_idname = 'file.open_config'
    bl_label = 'Open Config File'
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        os.startfile(config_filepath)
        return {'FINISHED'}
    

# Add to a menu
def menu_func_export(self, context):
    self.layout.operator(ExportBin.bl_idname, text='Bin file (.bin) (NewDark Toolkit)')

def menu_func_import(self, context):
    self.layout.operator(ImportE.bl_idname, text='E file (.e) (NewDark Toolkit)')

classes = (
            ImportE, 
            ExportBin,MaterialPropertiesPanel, 
            ImportMaterialFromCustomProps, 
            OpenConfigFile, 
            BSPExportParams
            )

def register():
    for c in classes:
        bpy.utils.register_class(c)
    
    bpy.types.Material.shader = EnumProperty(name='Shader Type', description='Face/vertex brigtness type.',
        items = [ 
            ('PHONG', 'PHONG', 'Face brightness smoothly blended between brightness of each vertex. Smooth edges. [Note: true Phong is not supported by the Dark Engine, it will automatically use Gouraud.'), 
            ('GOURAUD', 'GOURAUD', 'Face brightness smoothly blended between brightness of each vertex. Smooth edges.'),
            ('FLAT', 'FLAT', 'Face evenly lit, using the brightness of the centre. Hard edges.') 
        ]
    )
    bpy.types.Material.transp = IntProperty(name='Transparency', description='How transpent this material is. 0 = opaque (default), 100 = transparent', min=0, max=100, step=1)
    bpy.types.Material.illum = IntProperty(name='Illumination', description='Material brightness. 0 = use natural lighting (default), 100 = fully illuminated', min=0, max=100, step=1)
    bpy.types.Material.dbl = BoolProperty(name='Double Sided', description='Draw material from front and back of face')
    bpy.types.Material.nocopy = BoolProperty(name='Do Not Copy Texture', description='Do not copy this texture when the object is exported. E.g. select this if the texture is orginally from a .crf file, or you don\'t want to overwrite it in txt16')
    
    #additional BSP params
    bpy.types.Scene.bspParams = StringProperty(name='', description = 'Additional params for BSP file conversion. The addon already uses Infile, Outfile, Coplanar Limit (ep), Opt level (l), Verbose (V), Centering (o), and Smooth Angle (M), but it supports many more. Run BSP from the command prompt with no params to see the full list')
    
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)
    #2.80: TOPBAR_MT was INFO_MT

def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)

    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    #2.80: TOPBAR_MT was INFO_MT

# NOTES:
# why add 1 extra vertex? and remove it when done? - 'Answer - eekadoodle - would need to re-order UV's without this since face order isnt always what we give blender, BMesh will solve :D'
# disabled scaling to size, this requires exposing bb (easy) and understanding how it works (needs some time)

if __name__ == '__main__':
    register()
