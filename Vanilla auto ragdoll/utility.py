import bmesh
import bpy
from mathutils import Matrix


def select_single(obj):
    """
    Deselect all the objects and then set the specified one selected and active.
    Same as clicking object in the viewport.
    """
    # perhaps there is a builtin/better way to select one specific object
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def isolate_vertex_group(mesh, vgroup_index, threshold=0.9):
    """
    Isolate a vertex group with the given index by dissolving geometry with weight under the threshold.
    """
    bm = bmesh.new()
    bm.from_mesh(mesh)
    deform_layer = bm.verts.layers.deform.active
    dissolved_verts = [v for v in bm.verts if
                       (v[deform_layer][vgroup_index] < threshold if vgroup_index in v[deform_layer] else True)]
    bmesh.ops.dissolve_verts(bm, verts=dissolved_verts)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

# TODO: Documentation
def delete_loose(mesh):
    bm = bmesh.new()
    bm.from_mesh(mesh)
    verts = [v for v in bm.verts if not v.link_faces]
    for v in verts:
        bm.verts.remove(v)
    bm.to_mesh(mesh)
    mesh.update()
    bm.clear()


def apply_modifiers(obj):
    obj.data = obj.to_mesh()
    obj.modifiers.clear()


def bone_center_matrix(bone):
    return bone.matrix_local @ Matrix.Translation((0, bone.length / 2, 0))


def transform_origin(obj, transformation: Matrix):
    """
    Transform the object with the specified transformation and its data with the inversion of that transformation.
    The mesh data stays the same relative to the global coordinates while the origin object gets transformed.
    """
    obj.matrix_world = obj.matrix_world @ transformation
    obj.data.transform(transformation.inverted())


def offset_empty(obj, offset: Matrix):
    """
    This is a workaround for constraints like 'copy rotation' where there is no offset option.
    :offset: Local matrix for the created empty.
    :returns: An empty object parented to the specified one. In a constraint it should be assigned as target
    and used as an offset.
    """
    empty = bpy.data.objects.new(f'{obj.name} offset empty', None)
    empty.empty_display_type = 'SINGLE_ARROW'
    empty.parent = obj
    empty.matrix_local = offset
    return empty
