import math

import bpy
from math import radians
from mathutils import Matrix, Quaternion, Euler
from .utility import select_single, isolate_vertex_group, transform_origin, offset_empty, bone_center_matrix, \
    delete_loose, scripted_driver_add, driver_object_var_add
from typing import Literal  # Note: PEP 586 - Literal types


class AutoRagdollError(Exception):
    pass


class RagdollSegment:
    def __init__(self, obj, parent_bone):
        self.obj = obj
        self.parent_bone = parent_bone


# TODO: Add drivers to the bone constraints to allow ragdoll animation
# TODO: Implement bone selection
class BaseRagdoll:
    def __init__(self, context, armature):
        self.armature = armature

        if self.armature.type != 'ARMATURE':
            raise AutoRagdollError(
                f'The type object type of "{armature.name}" is "{armature.type}". '
                f'Select an armature object and try again')

        self.ragdoll_enabled_prop_name = 'Ragdoll enabled'
        self.armature[self.ragdoll_enabled_prop_name] = True
        enabled = self.armature.id_properties_ui(self.ragdoll_enabled_prop_name)
        enabled.update(default=True, description='Ragdoll enabled state')

        self.armature.data.pose_position = 'REST'
        self.segments = set()
        self.ragdoll_collection = bpy.data.collections.new(f'{self.armature.name} ragdoll')
        self.segment_collection = bpy.data.collections.new(f'{self.armature.name} ragdoll segments')
        self.joint_collection = bpy.data.collections.new(f'{self.armature.name} ragdoll joints')
        self.ragdoll_collection.children.link(self.segment_collection)
        self.ragdoll_collection.children.link(self.joint_collection)
        context.scene.collection.children.link(self.ragdoll_collection)

        self.create_segments()
        self.connect_segments()

        self.armature.data.pose_position = 'POSE'
        select_single(self.armature)

    def create_segments(self):
        raise NotImplemented

    def add_segment(self, segment, pose_bone, copy_rotation_offset: Quaternion = None):

        if pose_bone.parent:
            copy_rotation_constraint = pose_bone.constraints.new('COPY_ROTATION')
            if copy_rotation_offset:
                empty = offset_empty(segment, copy_rotation_offset.to_matrix().to_4x4())
                self.segment_collection.objects.link(empty)
                empty.empty_display_size = 0.2 * pose_bone.bone.length  # 0.2 is arbitrary
                copy_rotation_constraint.target = empty
            else:
                copy_rotation_constraint.target = segment

            driver = scripted_driver_add(copy_rotation_constraint, 'influence')
            var = driver_object_var_add(driver, self.armature, self.ragdoll_enabled_prop_name)
            driver.expression = var.name
        else:
            child_of_constraint = pose_bone.constraints.new('CHILD_OF')
            child_of_constraint.target = segment

            child_of_constraint.use_scale_x = False
            child_of_constraint.use_scale_y = False
            child_of_constraint.use_scale_z = False

            driver = scripted_driver_add(child_of_constraint, 'influence')
            var = driver_object_var_add(driver, self.armature, self.ragdoll_enabled_prop_name)
            driver.expression = var.name

        self.segments.add(RagdollSegment(segment, pose_bone))

    def connect_segments(self):
        # The segment parenting logic is poorly written and unoptimized
        # TODO: This method requires a revision
        for child_segment in self.segments:
            if child_segment.parent_bone.parent:
                for parent_segment in self.segments:
                    if parent_segment.parent_bone == child_segment.parent_bone.parent:
                        joint = bpy.data.objects.new(f'{parent_segment.obj.name} & {child_segment.obj.name}', None)
                        joint.parent = self.armature
                        joint.matrix_world = self.armature.matrix_world @ child_segment.parent_bone.bone.matrix_local
                        self.joint_collection.objects.link(joint)
                        joint.empty_display_type = 'ARROWS'
                        joint.empty_display_size = 0.2 * child_segment.parent_bone.bone.length  # 0.2 is arbitrary
                        select_single(joint)

                        bpy.ops.rigidbody.constraint_add(type='GENERIC')
                        constraint = joint.rigid_body_constraint
                        constraint.object1 = parent_segment.obj
                        constraint.object2 = child_segment.obj
                        constraint.disable_collisions = False

                        # This block of code sets the location and rotation limits
                        # allowing the colliders to only rotate and not move
                        constraint.use_limit_ang_x = True
                        constraint.use_limit_ang_y = True
                        constraint.use_limit_ang_z = True
                        constraint.use_limit_lin_x = True
                        constraint.use_limit_lin_y = True
                        constraint.use_limit_lin_z = True
                        constraint.limit_lin_x_lower = 0
                        constraint.limit_lin_x_upper = 0
                        constraint.limit_lin_y_lower = 0
                        constraint.limit_lin_y_upper = 0
                        constraint.limit_lin_z_lower = 0
                        constraint.limit_lin_z_upper = 0

                        # Break since there can only be one parent
                        break


class SimpleRagdoll(BaseRagdoll):
    CUBE_VERTS = [(1.0, 1.0, -1.0), (1.0, -1.0, -1.0), (-1.0, -1.0, -1.0), (-1.0, 1.0, -1.0),
                  (1.0, 1.0, 1.0), (1.0, -1.0, 1.0), (-1.0, -1.0, 1.0), (-1.0, 1.0, 1.0)]
    CUBE_FACES = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (4, 0, 3, 7)]

    def __init__(self, context, segment_shape: Literal['BOX', 'CAPSULE', 'CYLINDER'] = 'BOX'):
        self.segment_shape = segment_shape
        super().__init__(context, context.active_object)

    def create_segments(self):
        for pose_bone in self.armature.pose.bones:
            bone = pose_bone.bone
            bone_name = bone.name

            cube = bpy.data.meshes.new(f'{bone_name} collider')
            cube.from_pydata(self.CUBE_VERTS, [], self.CUBE_FACES)

            segment = bpy.data.objects.new(bone_name, cube)
            self.segment_collection.objects.link(segment)
            select_single(segment)
            segment.parent = self.armature
            segment.rotation_mode = 'QUATERNION'

            # 0.1 is an arbitrary representation of the default style bone head to tail ratio
            radius = 0.1 * bone.length
            scalem = (Matrix.Scale(radius, 4, (1, 0, 0)) @
                      Matrix.Scale(bone.length / 2 * 0.9, 4, (0, 1, 0)) @
                      Matrix.Scale(radius, 4, (0, 0, 1)))
            segment.matrix_world = (self.armature.matrix_world @
                                    bone_center_matrix(bone) @
                                    scalem @
                                    Matrix.Rotation(radians(-90), 4, (1, 0, 0)))
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

            segment.display_type = "WIRE"
            segment.hide_render = True

            bpy.ops.rigidbody.object_add(type='ACTIVE')
            segment.rigid_body.collision_shape = self.segment_shape

            # This block of code creates and rotates an empty to align y-axis of the bone to z-axis of the segment mesh.
            # it would be nice to have an 'add rotation constraint'
            # or some 'offset by rotation' option in the copy rotation constraint.
            if pose_bone.parent:
                self.add_segment(segment, pose_bone, copy_rotation_offset=Euler((radians(90), 0, 0)).to_quaternion())
            else:
                self.add_segment(segment, pose_bone)


class RagdollFromVGroups(BaseRagdoll):
    def __init__(self, context, hide_original_mesh=False, remesh=True, voxel_size=0.1,
                 segment_shape: Literal['CONVEX_HULL', 'MESH'] = 'CONVEX_HULL'):
        self.remesh = remesh
        self.voxel_size = voxel_size
        self.segment_shape = segment_shape
        armature = None
        self.ragdoll_mesh = None

        selected_objects = context.selected_objects
        if len(selected_objects) != 2:
            raise AutoRagdollError('Select an armature and a mesh')

        for obj in selected_objects:
            if obj.type == 'MESH':
                self.ragdoll_mesh = obj
            elif obj.type == 'ARMATURE':
                armature = obj

        if armature is None or self.ragdoll_mesh is None:
            raise AutoRagdollError('Select an armature and a mesh')

        super().__init__(context, armature)

        if hide_original_mesh:
            self.ragdoll_mesh.hide_viewport = True

    def create_segments(self, threshold=0.9):
        for pose_bone in self.armature.pose.bones:
            bone_name = pose_bone.name
            segment = self.ragdoll_mesh.copy()
            segment.data = self.ragdoll_mesh.data.copy()
            segment.name = f'{bone_name} collider'
            segment.data.name = f'{bone_name} collider'
            self.segment_collection.objects.link(segment)
            select_single(segment)
            bpy.ops.object.convert()
            for g in segment.vertex_groups:
                if g.name == bone_name:
                    vertex_group_index = g.index
                    break
            else:
                raise AutoRagdollError(f'Missing vertex group "{bone_name}"')

            isolate_vertex_group(segment.data, vertex_group_index, threshold=threshold)

            # Align the bone segment with its corresponding bone
            transform_origin(segment, segment.rotation_quaternion.to_matrix().to_4x4() @
                             bone_center_matrix(pose_bone.bone))

            delete_loose(segment.data)
            if self.remesh:
                remesh_mod = segment.modifiers.new(name="Remesh", type='REMESH')
                remesh_mod.voxel_size = self.voxel_size
                bpy.ops.object.convert()

            bpy.ops.rigidbody.object_add(type='ACTIVE')
            segment.rigid_body.collision_shape = self.segment_shape
            self.add_segment(segment, pose_bone)
