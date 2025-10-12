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
    'author': 'Tom N Harris, 2.80/2.9x/3.x/4.x update by Robin Collier, including adaptions from the Dark Exporter 2 by Elendir',
    'version': (1, 6, 4),
    'blender': (4, 1),
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
from . import utils
from bpy.props import StringProperty, FloatProperty, BoolProperty, EnumProperty, IntProperty
from bpy_extras.io_utils import ImportHelper, ExportHelper, axis_conversion

default_config = {
'ai_mesh': False,
'bsp_optimization': 0,
'centering': True,
'selection_only': False,
'smooth_angle': 89,
'game_dirs': 'C:\\Games\\Thief2',
'bsp_meshbld_dir': 'C:\\some\\path\\to\\folder\\containing\\BSP and meshbld etc',
'wineprefix': os.getenv('HOME') + '/.wine',
'autodel': False,
'bin_copy': True,
'tex_copy': 1,
'black_tex_fix_4.2': False,
'joint_plane_rgba': (0.0, 0.96, 0.0, 1.0)
}

config_filename = 'Bin_Export.cfg'
config_path = bpy.utils.user_resource('CONFIG', path='scripts', create=True)
config_filepath = os.path.join(config_path, config_filename)
game_dirs = []

def load_config():
    with open(config_filepath, 'r') as config_file:
        return json.load(config_file)

try:
    config_from_file = load_config()
except IOError:
    with open(config_filepath, 'w') as config_file:
        json.dump(default_config, config_file, indent=4, sort_keys=True)
    config_from_file = load_config()

def addDefaultValueToConfigFile(keyToSet):
    config_from_file[keyToSet] = default_config[keyToSet] #add missing key with default value
    config_update = open(config_filepath, 'w')
    json.dump(config_from_file, config_update, indent = 4, sort_keys = True)
    config_update.close()
    load_config()
    
#Try to get a value from a config file. If key not found, set default value then return that.
def tryConfig(key, config_from_file):
    try:
        return config_from_file[key]
    except:
        addDefaultValueToConfigFile(key)    
        return config_from_file[key]
        
def tryGetFMDir():
    try:
        return bpy.context.scene.fmDir
    except:
        return ''

class ImportE(bpy.types.Operator, ImportHelper):
    """Import from E file format (.e)"""
    bl_idname = 'import_scene.efile'
    bl_label = 'Import E file'

    filename_ext = '.e'
    filter_glob: StringProperty(default='*.e', options={'HIDDEN'})

    use_image_search: BoolProperty(name='Texture Search', description='Search subdirectories for any associated textures. Also searches the textures dir set in User Preferences.  (Warning, may be slow)', default=False)

    version = bpy.app.version_file
    major = version[0]
    minor = version[1]
 
    if major >= 4 and minor >= 2:
        black_tex_fix: BoolProperty(name='Black Texture Workaround (4.2+)', 
        description='For Blender version 4.2, some older graphics cards (maybe just AMD) cannot apply lighting to textures in "Material Preview" mode. If that affects you, select this setting to enable a workaround (uses an Emission shader instead of Diffuse)', 
        default=tryConfig('black_tex_fix_4.2', config_from_file))

    joint_plane_rgba: bpy.props.FloatVectorProperty(
        name='Joint/Limit Plane Colour',
        description='Choose your preferred colour for joints and limit places. Assumes these objects have a material name of "Green"',
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=tryConfig('joint_plane_rgba', config_from_file)
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
        from . import import_e

        keywords = self.as_keywords(ignore=('axis_forward', 'axis_up', 'filter_glob'))

        global_matrix = axis_conversion(from_forward=self.axis_forward, from_up=self.axis_up).to_4x4()
        keywords['global_matrix'] = global_matrix

        return import_e.load(self, context, **keywords)

class ExportBin(bpy.types.Operator, ExportHelper):
    """Export to Bin file format (.bin)"""
    bl_idname = 'export_scene.binfile'
    bl_label = 'Export Bin file'
    filename_ext = '.bin'
    filter_glob: StringProperty(default='*.bin', options={'HIDDEN'})
    bl_options = {'PRESET'}
        
    wineprefix: StringProperty(default=tryConfig('wineprefix', config_from_file), name='Wine prefix', description='Wine prefix to use while executing BSP.exe and/or MeshBld.exe (Linux only)')
    bsp_dir: StringProperty(default=tryConfig('bsp_meshbld_dir', config_from_file), name='BSP/MeshBld Dir', description='Folder containing BSP.exe and/or MeshBld.exe')
    
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
        keywords['use_selection'] = context.scene.use_selection
        keywords['centering'] = context.scene.centering
        keywords['apply_modifiers'] = context.scene.apply_modifiers
        keywords['smooth_angle'] = context.scene.smooth_angle
        keywords['bsp_optimization'] = context.scene.bsp_optimization
        keywords['use_coplanar_limit'] = context.scene.use_coplanar_limit
        keywords['coplanar_limit'] = context.scene.coplanar_limit
        keywords['ai_mesh'] = context.scene.ai_mesh
        keywords['mesh_type'] = context.scene.mesh_type
        keywords['bin_copy'] = context.scene.bin_copy
        keywords['game_dirs'] = game_dirs
        keywords['game_dir_ID'] = context.scene.game_dir_ID
        keywords['autodel'] = context.scene.autodel
        keywords['tex_copy'] = context.scene.tex_copy
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
        layout.row().prop(activeMat, 'filename_override')
        layout.row().separator()
        layout.row().operator('material.import_from_custom', icon = 'MATERIAL')

class ImportMaterialFromCustomProps(bpy.types.Operator):
    """Old version of this addon used custom properties created by the user. Now obsolete. This function will search for them and apply their values to the above"""
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
    bl_context = 'scene'
    bl_label = 'Object Export Params (NewDark Toolkit)'

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        row = col.row()
        row.prop(context.scene, 'use_selection')
        row.prop(context.scene, 'centering')
        row.prop(context.scene, 'apply_modifiers')
        layout.row().prop(context.scene, 'smooth_angle')
        layout.row().prop(context.scene, 'bsp_optimization')
        
        col2 = layout.column()
        row2 = col2.row()
        row2.prop(context.scene, 'use_coplanar_limit')
        if(context.scene.use_coplanar_limit):
            row2.prop(context.scene, 'coplanar_limit')
        
        col3 = layout.column()
        row3 = col3.row()
        row3.prop(context.scene, 'ai_mesh')
        if(context.scene.ai_mesh):
            row3.prop(context.scene, 'mesh_type')
        
        layout.row().prop(context.scene, 'bin_copy')
        if(context.scene.bin_copy):
            layout.row().prop(context.scene, 'game_dir_ID')
        
        layout.row().prop(context.scene, 'tex_copy')
        layout.row().prop(context.scene, 'autodel')
        layout.row().prop(context.scene, 'bspParams')
        layout.row().label(text='NOTE: Incorrect/duplicate params may cause conversion errors.')
        layout.row().operator('file.open_config', icon = 'SETTINGS')
        
class OpenConfigFile(bpy.types.Operator):
    """Open the config file to change the default values for this addon. Blender must be closed and restarted for the changes to take effect. Be careful with the file structure"""
    bl_idname = 'file.open_config'
    bl_label = 'Open Config File'
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        utils.open_file(config_filepath)
        return {'FINISHED'}
    

# Add to a menu
def menu_func_export(self, context):
    self.layout.operator(ExportBin.bl_idname, text='Bin file (.bin) (NewDark Toolkit)')

def menu_func_import(self, context):
    self.layout.operator(ImportE.bl_idname, text='E file (.e) (NewDark Toolkit)')

classes = (
            ImportE, 
            ExportBin,
            MaterialPropertiesPanel, 
            ImportMaterialFromCustomProps, 
            OpenConfigFile, 
            BSPExportParams
            )

def replaceStringLiteralWinePrefixWithValueFromOS():
    existingWinePrefix = tryConfig('wineprefix', config_from_file)
    if existingWinePrefix == '$HOME/.wine':
        addDefaultValueToConfigFile('wineprefix')

def register():
    for c in classes:
        bpy.utils.register_class(c)
    
    bpy.types.Material.shader = EnumProperty(name='Shader Type', description='Face/vertex brightness type.',
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
    bpy.types.Material.filename_override = StringProperty(name='Filename Override', description='Use this if you have a complex material setup and the exporter cannot work out what texture to assign. TEXTURE MUST BE LOADED INTO THE SCENE')
    
    #export param property declarations
    bpy.types.Scene.use_selection = BoolProperty(name='Selection Only', description='Export selected objects only', default=False)
    bpy.types.Scene.centering = BoolProperty(name='Center object', default=tryConfig('centering', config_from_file), description='Center your object near its centroid')
    bpy.types.Scene.apply_modifiers = BoolProperty(name='Apply Modifiers', description='Apply modifiers to exported object.', default = True)
    bpy.types.Scene.smooth_angle = IntProperty(name='Smooth Angle', min=0, max=360, step=1, description='Max angle between faces that should be smoothly shaded. Default: 120. Only applies to Phong/Gouraud materials', default=tryConfig('smooth_angle', config_from_file))
    bpy.types.Scene.bsp_optimization = IntProperty(name='BSP Optimization', min=0, max=3, step=1, description='BSP Optimization levels (0: Cleanest model, opaque/alpha keyed materials only, 3: Messy triangles, but required for transparent materials)', default=0)
    bpy.types.Scene.use_coplanar_limit = BoolProperty(name='Use Coplanar Limit', description='Disable this if you can see errors in your object\'s shape', default = True)
    bpy.types.Scene.coplanar_limit = FloatProperty(name='', description='Change this if you get small gaps in the model or flattened faces', default = 1.0)
    bpy.types.Scene.bin_copy = BoolProperty(name='Bin Copy', default=tryConfig('bin_copy', config_from_file), description='Copy model to your FM\'s OBJ or MESH subfolder. Saves you having to find it each time you export this object')
    
    #generate game dirs list
    gDirsString = tryConfig('game_dirs', config_from_file)
    split = gDirsString.split(';')
    enum_dirs = []
    #game_dirs = []
    for i in range(0, len(split)):
       enum_dirs.append((str(i), split[i].strip(), ''))
       game_dirs.append(split[i].strip())
    
    bpy.types.Scene.game_dir_ID = EnumProperty(name='FM/Game Folder Presets', items = enum_dirs, description='NewDark-style "FMs\..." folder, or folder containing Thief/Thief2.exe, Dromed.exe, Shock2.exe etc')
    #bpy.types.Scene.fmDir = StringProperty(name='FM/Game Folder', description = 'FM Folder, or folder containing Thief/Thief2.exe, Dromed.exe, Shock2.exe etc. OBJ or MESH folders added automatically based on whether or not "AI Mesh" is selected')
    bpy.types.Scene.autodel = BoolProperty(name='Delete temp files', default=tryConfig('autodel', config_from_file), description='Delete local temporary files. Only deletes bin/cal files if they files were copied to your OBJ or MESH folder. e file will be deleted regardless of copy option')
    bpy.types.Scene.tex_copy = EnumProperty(name='Copy Textures', items=(('0', 'Never', ''), ('1', 'Only if not present', ''), ('2', 'Always', '')), default='1', description='Copy textures to obj (or mesh)\\txt16. Default = Only when texture isn\'t already in txt16')
    bpy.types.Scene.ai_mesh = BoolProperty(name='AI Mesh', description='Use MeshBld and a .cal file (see the menu on the right) to export to the mesh folder', default=False)
    bpy.types.Scene.mesh_type = EnumProperty(
            name='Type',
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
    
    bpy.types.Scene.bspParams = StringProperty(name='Extra BSP Params', description = 'Additional params for BSP file conversion. The addon already uses Infile, Outfile, Coplanar Limit (ep), Opt level (l), Verbose (V), Centering (o), and Smooth Angle (M), but it supports many more. Run BSP from the command prompt with no params to see the full list')
    
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)
    
    replaceStringLiteralWinePrefixWithValueFromOS()

def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)

    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)

# NOTES:
# why add 1 extra vertex? and remove it when done? - 'Answer - eekadoodle - would need to re-order UV's without this since face order isnt always what we give blender, BMesh will solve :D'
# disabled scaling to size, this requires exposing bb (easy) and understanding how it works (needs some time)

if __name__ == '__main__':
    register()
