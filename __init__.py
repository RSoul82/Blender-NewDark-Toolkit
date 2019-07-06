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
    "name": "Blender NewDark Toolkit",
    "author": "Tom N Harris, 2.80 update by Robin Collier, including adaptions from the Dark Exporter 2 by Elendir",
    "blender": (2, 80, 0),
    "location": "File > Import-Export",
    "description": "Import E files, Export Bin, including textures",
    "warning": "experimental",
#    "wiki_url": "",
#    "tracker_url": "",
#    "support": '',
    "category": "Import-Export"}

# To support reload properly, try to access a package var, if it's there, reload everything
if "bpy" in locals():
    import importlib
    if "import_e" in locals():
        importlib.reload(import_e)
    if "export_bin" in locals():
        importlib.reload(export_bin)


import bpy
import os
import json
from bpy.props import StringProperty, FloatProperty, BoolProperty, EnumProperty, IntProperty
from bpy_extras.io_utils import ImportHelper, ExportHelper, axis_conversion

default_config = {
"bsp_optimization": 0,
"centering": True,
"selection_only": False,
"game_dir1": "C:\\Games\\Thief2",
"game_dir2": "",
"game_dir3": "",
"game_dir4": "",
"game_dir5": "",
"bsp_dir": "C:\\Games\\Thief2\\Tools\\3dstobin\\3ds\\Workshop",
"autodel": False,
"bin_copy": True,
"tex_copy": 2
}

config_filename = "Bin_Export.cfg"
config_path = bpy.utils.user_resource('CONFIG', path='scripts', create=True)
config_filepath = os.path.join(config_path, config_filename)
try:
    config_file = open(config_filepath, 'r')
    config_from_file = json.load(config_file)
except IOError:
    config_file = open(config_filepath, 'w')
    json.dump(default_config, config_file, indent=4, sort_keys=True)
    config_file.close()
    config_file = open(config_filepath, 'r')
    config_from_file = json.load(config_file)
    config_file.close()
    
#Try to get a value from a config file. Return ... if key not founnd.
def tryConfig(key, config_from_file):
    try:
        return config_from_file[key]
    except:
        return ''

class ImportE(bpy.types.Operator, ImportHelper):
    '''Import from E file format (.e)'''
    bl_idname = "import_scene.efile"
    bl_label = 'Import E file'

    filename_ext = ".e"
    filter_glob: StringProperty(default="*.e", options={'HIDDEN'})

    use_image_search: BoolProperty(name="Texture Search", description="Search subdirectories for any associated textures. Also searches the textures dir set in User Preferences.  (Warning, may be slow)", default=False)

    axis_forward: EnumProperty(
            name="Forward",
            items=(('X', "X Forward", ""),
                   ('Y', "Y Forward", ""),
                   ('Z', "Z Forward", ""),
                   ('-X', "-X Forward", ""),
                   ('-Y', "-Y Forward", ""),
                   ('-Z', "-Z Forward", ""),
                   ),
            default='Y',
            )

    axis_up: EnumProperty(
            name="Up",
            items=(('X', "X Up", ""),
                   ('Y', "Y Up", ""),
                   ('Z', "Z Up", ""),
                   ('-X', "-X Up", ""),
                   ('-Y', "-Y Up", ""),
                   ('-Z', "-Z Up", ""),
                   ),
            default='Z',
            )

    def execute(self, context):
        from . import import_e

        keywords = self.as_keywords(ignore=("axis_forward", "axis_up", "filter_glob"))

        global_matrix = axis_conversion(from_forward=self.axis_forward, from_up=self.axis_up).to_4x4()
        keywords["global_matrix"] = global_matrix

        return import_e.load(self, context, **keywords)


class ExportBin(bpy.types.Operator, ExportHelper):
    '''Export to Bin file format (.bin)'''
    bl_idname = "export_scene.binfile"
    bl_label = 'Export Bin file'
    
    filename_ext = ".bin"
    filter_glob: StringProperty(default="*.bin", options={'HIDDEN'})

    use_selection: BoolProperty(name="Selection Only", description="Export selected objects only", default=False)
    centering: BoolProperty(name="Center object", default=config_from_file["centering"], 
    description="Center your object near its centroid.")
    apply_modifiers: BoolProperty(name="Apply Modifiers", description="Apply modifiers to exported object.", default = True)
    game_dir_ID: IntProperty(default=1, name="Game Dir No.", min=1, max=5, step=1, 
    description="Which of the following game dirs to export this object to..")

    bsp_optimization: IntProperty(default=0, name="BSP Optimization", min=0, max=3, step=1, 
    description="BSP Optimization levels (0 recommended)")
    ep: FloatProperty(default=0.0, name="Poly Merge Epsilon", 
    description="Change this if you have problems with small gaps in the model caused by triangle merging (0.0 recommended)")
    
    axis_forward: EnumProperty(
            name="Forward",
            items=(('X', "X Forward", ""),
                   ('Y', "Y Forward", ""),
                   ('Z', "Z Forward", ""),
                   ('-X', "-X Forward", ""),
                   ('-Y', "-Y Forward", ""),
                   ('-Z', "-Z Forward", ""),
                   ),
            default='Y',
            )

    axis_up: EnumProperty(
            name="Up",
            items=(('X', "X Up", ""),
                   ('Y', "Y Up", ""),
                   ('Z', "Z Up", ""),
                   ('-X', "-X Up", ""),
                   ('-Y', "-Y Up", ""),
                   ('-Z', "-Z Up", ""),
                   ),
            default='Z',
            )
    
    bsp_dir: StringProperty(default=tryConfig('bsp_dir', config_from_file), name="BSP Dir", 
    description="Folder containing BSP.exe")
    game_dir1: StringProperty(default=tryConfig('game_dir1', config_from_file), name="Game Dir 1", 
    description="Folder containing Thief/Thief2/Shock2/Dromed.exe etc")
    game_dir2: StringProperty(default=tryConfig('game_dir2', config_from_file), name="Game Dir 2", 
    description="(Optional) Alternate folder containing Thief/Thief2/Shock2/Dromed.exe etc")
    game_dir3: StringProperty(default=tryConfig('game_dir3', config_from_file), name="Game Dir 3", 
    description="(Optional) Alternate folder containing Thief/Thief2/Shock2/Dromed.exe etc")
    game_dir4: StringProperty(default=tryConfig('game_dir4', config_from_file), name="Game Dir 4", 
    description="(Optional) Alternate folder containing Thief/Thief2/Shock2/Dromed.exe etc")
    game_dir5: StringProperty(default=tryConfig('game_dir5', config_from_file), name="Game Dir 5", 
    description="(Optional) Alternate folder containing Thief/Thief2/Shock2/Dromed.exe etc")
    bin_copy: BoolProperty(name="Bin Copy", default=config_from_file["bin_copy"],
    description="Copy model to obj subfolder")
    autodel: BoolProperty(name="Delete temp files", default=config_from_file["autodel"],
    description="Delete local temporary files.")
    tex_copy: EnumProperty(name="Copy Textures", items=(("0", "Never", ""), ("1", "Only if not present", ""), ("2", "Always", "")), default="1",
    description="Copy textures to obj\\txt16. Default = Only when texture isn't already in txt16")
    
    def execute(self, context):
        from . import export_bin

        keywords = self.as_keywords(ignore=("axis_forward", "axis_up", "filter_glob", "check_existing"))
        global_matrix = axis_conversion(to_forward=self.axis_forward, to_up=self.axis_up).to_4x4()
        keywords["global_matrix"] = global_matrix

        return export_bin.save(self, context, **keywords)

# Add to a menu
def menu_func_export(self, context):
    self.layout.operator(ExportBin.bl_idname, text="Bin file (.bin)")


def menu_func_import(self, context):
    self.layout.operator(ImportE.bl_idname, text="E file (.e)")

classes = (ImportE, ExportBin)

def register():
    for c in classes:
        bpy.utils.register_class(c)

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
# why add 1 extra vertex? and remove it when done? - "Answer - eekadoodle - would need to re-order UV's without this since face order isnt always what we give blender, BMesh will solve :D"
# disabled scaling to size, this requires exposing bb (easy) and understanding how it works (needs some time)

if __name__ == "__main__":
    register()
