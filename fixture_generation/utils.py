"""
Fixture creation utils.
"""

import numpy as np

import blenderproc as bproc
import bpy
from mathutils import Vector


def boolean_modifier(obj, target, name, operation):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select()
    bpy.context.view_layer.objects.active = obj.blender_obj
    modifier = obj.blender_obj.modifiers.new(type="BOOLEAN", name=name)
    modifier.object = target.blender_obj
    modifier.operation = operation
    modifier.solver = 'EXACT'
    modifier.use_self = True
    modifier.use_hole_tolerant = True

    bpy.ops.object.modifier_apply(modifier=name)


def add_tag_bevel(fixture, tag_loc, obj_mat, add_cube, tag_border):
    # add tag bevel
    bevel_cube_outside = bproc.object.create_primitive("CUBE")
    bevel_cube_outside.set_name('bevel_cube_outside')
    bevel_cube_outside.blender_obj.dimensions = [0.045, 0.045, 0.005]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bevel_cube_outside.set_location([tag_loc[0], tag_loc[1], tag_loc[2]])

    bevel_cube_inside = bproc.object.create_primitive("CUBE")
    bevel_cube_inside.set_name('bevel_cube_inside')
    bevel_cube_inside.blender_obj.dimensions = [0.04, 0.04, 0.01]
    bevel_cube_inside.set_location([tag_loc[0], tag_loc[1], tag_loc[2]])

    boolean_modifier(obj=bevel_cube_outside, target=bevel_cube_inside, name='bevel_cube', operation='DIFFERENCE')

    bevel_cube_inside.delete()
    bpy.context.view_layer.update()
    print('bevel mat', bevel_cube_outside.blender_obj.matrix_world)
    obj2tag_trafo = bevel_cube_outside.blender_obj.matrix_world.inverted() @ obj_mat

    # further cut the bevel cube such that printing is more secured, i.e. there remain connections
    cube = bproc.object.create_primitive("CUBE")
    cube.blender_obj.dimensions = [0.01, 1, 1]
    cube.set_location(bevel_cube_outside.get_location())
    boolean_modifier(obj=bevel_cube_outside, target=cube, name='slice_x', operation='DIFFERENCE')
    cube.delete()
    cube = bproc.object.create_primitive("CUBE")
    cube.blender_obj.dimensions = [1, 0.01, 1]
    cube.set_location(bevel_cube_outside.get_location())
    cube.set_rotation_euler([0., np.pi / 2., 0.])
    boolean_modifier(obj=bevel_cube_outside, target=cube, name='slice_x', operation='DIFFERENCE')
    cube.delete()

    # check if the fixture is large enough to hold the object, else put a cube on top of it
    if add_cube:
        cube = bproc.object.create_primitive("CUBE")
        xy_dims = 0.05 if tag_border else 0.04
        cube.blender_obj.dimensions = [xy_dims, xy_dims, 0.01]
        cube.set_location(bevel_cube_outside.get_location() + Vector([0., 0., 0.0025]))
        boolean_modifier(obj=fixture, target=cube, name='cube_top', operation='UNION')
        cube.delete()
        # shift the bevel cube
        bevel_cube_outside.set_location(bevel_cube_outside.get_location() + Vector([0., 0., 0.0075]))

    boolean_modifier(obj=fixture, target=bevel_cube_outside, name='tag_bevel', operation='DIFFERENCE')

    return obj2tag_trafo
