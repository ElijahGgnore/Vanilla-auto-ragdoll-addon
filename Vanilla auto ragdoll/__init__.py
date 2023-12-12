import sys
from importlib import reload
import bpy
from . import operators

bl_info = {
    "name": "Vanilla auto ragdoll",
    "version": (0, 1),
    "blender": (3, 0, 0),
    "category": "Object",
}

# This code block reloads all the submodules
submodules = [v for k, v in sys.modules.items() if k.startswith(__name__)]
for submodule in submodules:
    reload(submodule)


def draw_item(self, context):
    self.layout.separator()
    self.layout.operator(operators.SimpleRagdollOperator.bl_idname, text='Setup a simple ragdoll')
    self.layout.operator(operators.RagdollFromVGroupsOperator.bl_idname, text='Setup a remeshed ragdoll')
    self.layout.separator()


def register():
    bpy.utils.register_class(operators.SimpleRagdollOperator)
    bpy.utils.register_class(operators.RagdollFromVGroupsOperator)
    bpy.types.VIEW3D_MT_object.append(draw_item)


def unregister():
    bpy.types.VIEW3D_MT_object.remove(draw_item)
    bpy.utils.unregister_class(operators.SimpleRagdollOperator)
    bpy.utils.unregister_class(operators.RagdollFromVGroupsOperator)
