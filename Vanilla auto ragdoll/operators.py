import bpy
from . import auto_ragdoll


class SimpleRagdollOperator(bpy.types.Operator):
    bl_idname = "object.setup_simple_ragdoll"
    bl_label = "Setup a simple ragdoll"
    bl_options = {'REGISTER', 'UNDO'}
    segment_collider_shape: bpy.props.EnumProperty(name='Collider shape',
                                                   description='The simple shape used for ragdoll segments\' colliders',
                                                   items=[('BOX', 'Box', ''),
                                                          ('CAPSULE', 'Capsule', ''),
                                                          ('CYLINDER', 'Cylinder', '')])

    def execute(self, context):
        try:
            auto_ragdoll.SimpleRagdoll(context, segment_shape=self.segment_collider_shape)
        except auto_ragdoll.AutoRagdollError as error:
            self.report({'ERROR'}, error.args[0])
            return {'CANCELLED'}
        return {'FINISHED'}


class RagdollFromVGroupsOperator(bpy.types.Operator):
    bl_idname = "object.setup_remeshed_ragdoll"
    bl_label = "Setup a remeshed ragdoll"
    bl_options = {'REGISTER', 'UNDO'}
    hide_original_mesh: bpy.props.BoolProperty(name='Hide the original mesh in the viewport')
    remesh: bpy.props.BoolProperty(name='Remesh', default=True,
                                   description='Enable this to remesh the isolated vertex groups. '
                                               'Remeshed ragdoll segments should be more stable when used as rigid '
                                               'bodies since they represent the volume of the original mesh while '
                                               'removing poor geometry')
    voxel_size: bpy.props.FloatProperty(name='Voxel size for the remeshed colliders', min=0.0001, default=0.1,
                                        precision=4, step=1,
                                        description='Lower this value for better representation of the original mesh. '
                                                    'Setting low values (around 0.001) may result in blender crashing')
    collision_shape: bpy.props.EnumProperty(name='Collider shape',
                                            description='The shape used for ragdoll segments\' colliders'
                                                        'Mesh shape is more computationally heavy, allows more '
                                                        'complex geometry but works bad with poor geometry',
                                            items=[('CONVEX_HULL', 'Convex hull', ''),
                                                   ('MESH', 'Mesh', '')])

    def execute(self, context):
        try:
            auto_ragdoll.RagdollFromVGroups(context, hide_original_mesh=self.hide_original_mesh, remesh=self.remesh,
                                            voxel_size=self.voxel_size)
        except auto_ragdoll.AutoRagdollError as error:
            self.report({'ERROR'}, error.args[0])
            return {'CANCELLED'}
        return {'FINISHED'}
