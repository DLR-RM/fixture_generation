import blenderproc as bproc
import bpy

from fixture_generation.utils import boolean_modifier, add_tag_bevel


def create_fixture_cylinder(obj, fixture_dims, fixture_loc, fixture_height, offset):
    obj.set_location([0., 0., -obj.get_bound_box().min(axis=0)[-1]])
    bpy.context.view_layer.update()
    obj_mat = obj.blender_obj.matrix_world.copy()
    bbox = obj.get_bound_box()

    # add a cylinder that represents the object
    cylinder = bproc.object.create_primitive('CYLINDER', vertices=500)
    diameter = max(bbox[:, 0].max() - bbox[:, 0].min(), bbox[:, 1].max() - bbox[:, 1].min()) + offset
    cylinder.blender_obj.dimensions = [diameter, diameter, bbox[:, 2].max()]
    cylinder.set_location([
        (bbox[:, 0].max() + bbox[:, 0].min()) / 2,
        (bbox[:, 1].max() + bbox[:, 1].min()) / 2,
        (bbox[:, 2].max() + bbox[:, 2].min()) / 2])

    # add a cube for the fixture
    fixture = bproc.object.create_primitive('CUBE')
    fixture.set_location([fixture_loc[0], fixture_loc[1], bbox[:, 2].max() - (fixture_height / 2) + 0.005])
    fixture.blender_obj.dimensions = [fixture_dims[0], fixture_dims[1], fixture_height]

    # boolean
    boolean_modifier(obj=fixture, target=cylinder, name='boolean', operation='DIFFERENCE')

    # add tag bevel
    obj2tag_trafo = add_tag_bevel(fixture=fixture, tag_loc=[fixture_loc[0], fixture_loc[1], bbox[:, 2].max() + 0.005],
                                  obj_mat=obj_mat, add_cube=False, tag_border=False)
    print('obj2tag trafo', obj2tag_trafo)
    return fixture, obj2tag_trafo
