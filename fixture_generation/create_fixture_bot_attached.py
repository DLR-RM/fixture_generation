import blenderproc as bproc
import numpy as np
import bpy
from mathutils import Vector

from fixture_generation.utils import boolean_modifier, add_tag_bevel


def create_fixture_bot_attached(obj, fixture_height, open_side, tag_side, z_rot=0., scale_x=1., scale_y=1.):
    assert open_side != tag_side
    obj_dup = obj.duplicate()

    if z_rot != 0:
        obj.set_rotation_euler([0., 0., np.deg2rad(z_rot)])
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    if scale_x != 1 or scale_y != 1:
        obj.set_scale([scale_x, scale_y, 1])
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.set_location([0., 0., -obj.get_bound_box().min(axis=0)[-1]])
    obj_dup.set_location([0., 0., -obj_dup.get_bound_box().min(axis=0)[-1]])

    bpy.context.view_layer.update()
    obj_mat = obj.blender_obj.matrix_world.copy()
    # boolean to only get the bottom part of the object
    bbox = obj.get_bound_box()
    print('bbox before', bbox)
    cube = bproc.object.create_primitive("CUBE")
    cube.blender_obj.dimensions = [bbox[:, 0].max() - bbox[:, 0].min() + 0.02,
                                   bbox[:, 1].max() - bbox[:, 1].min() + 0.02, fixture_height]
    cube.set_location(
        ((bbox[:, 0].max() + bbox[:, 0].min()) / 2, (bbox[:, 1].max() + bbox[:, 1].min()) / 2, fixture_height / 2))

    boolean_modifier(obj=obj, target=cube, name='clip', operation='INTERSECT')
    cube.delete()
    bbox = obj.get_bound_box()

    fixture = bproc.object.create_primitive("CUBE")
    fixture.blender_obj.dimensions = [bbox[:, 0].max() - bbox[:, 0].min() + 0.02,
                                      bbox[:, 1].max() - bbox[:, 1].min() + 0.02, fixture_height]
    fixture.set_location(
        ((bbox[:, 0].max() + bbox[:, 0].min()) / 2, (bbox[:, 1].max() + bbox[:, 1].min()) / 2, fixture_height / 2))

    cube = bproc.object.create_primitive("CUBE")
    cube.blender_obj.dimensions = [bbox[:, 0].max() - bbox[:, 0].min(), bbox[:, 1].max() - bbox[:, 1].min(),
                                   fixture_height + 0.01]
    cube.set_location(
        ((bbox[:, 0].max() + bbox[:, 0].min()) / 2, (bbox[:, 1].max() + bbox[:, 1].min()) / 2, fixture_height / 2))

    # some boolean modifiers to remove internal parts
    boolean_modifier(obj=fixture, target=cube, name='internal_removal', operation='DIFFERENCE')
    cube.delete()

    # cut the fixture open
    cube = bproc.object.create_primitive("CUBE")
    x, y, z = fixture.get_location()
    if open_side == '+x':
        cube.set_location([1.0 + bbox[:, 0].max() - 0.001, y, z])
    elif open_side == '+y':
        cube.set_location([x, 1.0 + bbox[:, 1].max() - 0.001, z])
    elif open_side == '-x':
        cube.set_location([-1.0 + bbox[:, 0].min() + 0.001, y, z])
    elif open_side == '-y':
        cube.set_location([x, -1.0 + bbox[:, 1].min() + 0.001, z])
    else:
        raise NotImplementedError(f'Unknown option for `open_side`: `{open_side}`')

    boolean_modifier(obj=fixture, target=cube, name='side_removal', operation='DIFFERENCE')
    cube.delete()

    # add a cube for the tag location
    tag_cube = bproc.object.create_primitive("CUBE")
    tag_cube.blender_obj.dimensions = [0.05, 0.05, fixture_height]
    if tag_side == '+x':
        tag_cube.set_location([bbox[:, 0].max() + 0.03, y, z])
    elif tag_side == '+y':
        tag_cube.set_location([x, bbox[:, 1].max() + 0.03, z])
    elif tag_side == '-x':
        tag_cube.set_location([bbox[:, 0].min() - 0.03, y, z])
    elif tag_side == '-y':
        tag_cube.set_location([x, bbox[:, 1].min() - 0.03, z])
    else:
        raise NotImplementedError(f'Unknown option for tag_side: `{tag_side}`')

    boolean_modifier(obj=fixture, target=tag_cube, name='tag_cube_merge', operation='UNION')

    # add tag
    x, y, z = tag_cube.get_location()
    obj2tag_trafo = add_tag_bevel(fixture=fixture, tag_loc=tag_cube.get_location() + Vector(
        [0., 0., tag_cube.get_bound_box()[:, 2].max() - z]), obj_mat=obj_mat, add_cube=False, tag_border=True)

    # cleanup
    tag_cube.delete()

    return fixture, obj2tag_trafo
