import blenderproc as bproc
import numpy as np
import bpy
from blenderproc.python.types.MeshObjectUtility import scene_ray_cast, MeshObject
from mathutils import Vector
import bmesh
from tqdm import tqdm

from fixture_generation.utils import boolean_modifier, add_tag_bevel


def create_fixture_top_down(obj, fixture_dims, fixture_loc, z_loc, add_cube, solidify, postprocess, tag_border):
    obj.set_location([0., 0., -obj.get_bound_box().min(axis=0)[-1]])
    bpy.context.view_layer.update()
    obj_mat = obj.blender_obj.matrix_world.copy()
    print('mat', obj_mat)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bbox = obj.get_bound_box()

    # solidify to enlarge the object a little
    if solidify > 0.:
        bpy.ops.object.select_all(action='DESELECT')
        obj.select()
        bpy.context.view_layer.objects.active = obj.blender_obj
        modifier = obj.blender_obj.modifiers.new(type='SOLIDIFY', name='enlarge_obj')
        modifier.thickness = solidify
        modifier.offset = 0.
        modifier.use_rim = True
        modifier.use_rim_only = True
        bpy.ops.object.modifier_apply(modifier='enlarge_obj')

    # check fixture height - if -1 then just go fully downwards
    if fixture_loc[-1] == -1:
        fixture_loc[-1] = ((bbox.max(axis=0)[-1] - bbox.min(axis=0)[-1]) / 2) + 0.005

    # boolean to only work on parts of the object
    bpy.ops.object.select_all(action='DESELECT')
    cube = bproc.object.create_primitive("CUBE")
    cube.set_name('clip')
    cube.blender_obj.dimensions = [fixture_dims[0] + 0.01, fixture_dims[1] + 0.01, z_loc[1] - z_loc[0] + 0.01]
    cube.set_location([fixture_loc[0], fixture_loc[1], (z_loc[1] + z_loc[0]) / 2])
    bpy.ops.object.select_all(action='DESELECT')
    obj.select()
    bpy.context.view_layer.objects.active = obj.blender_obj
    boolean_modifier(obj=obj, target=cube, operation='INTERSECT', name='clip')
    cube.delete()

    top_plane = bproc.object.create_primitive(shape='PLANE')
    top_plane.set_name('top_plane')
    top_plane.set_location([0., 0., bbox.max(axis=0)[-1] + 1])  # todo set location based on obj bbox
    top_plane.blender_obj.dimensions = [np.abs(bbox).max(axis=0)[0] * 2 + 1, np.abs(bbox).max(axis=0)[1] * 2 + 1, 0.]

    bot_plane = bproc.object.create_primitive(shape='PLANE')
    bot_plane.set_name('bot_plane')
    bot_plane.set_location([0., 0., -0.01])  # todo set location based on fixture height?
    bot_plane.blender_obj.dimensions = [np.abs(bbox).max(axis=0)[0] * 2 + 1, np.abs(bbox).max(axis=0)[1] * 2 + 1, 0.]

    ### step 2: remove unnecessary stuff
    bpy.ops.object.select_all(action='DESELECT')
    obj.select()
    bpy.context.view_layer.objects.active = obj.blender_obj

    bpy.ops.object.mode_set(mode='EDIT')  # Toggle edit mode
    bpy.ops.mesh.select_mode(type='FACE')  # Change to face selection
    bpy.ops.mesh.select_all(action='DESELECT')  # Select all faces
    bpy.ops.object.mode_set(mode='OBJECT')

    for polygon in tqdm(obj.blender_obj.data.polygons):
        if polygon.normal[2] < 0:
            polygon.select = True
            continue

        face_hits_top_plane = False
        for vertex_index in polygon.vertices:
            # ray-cast
            hit, _, _, _, hit_obj, _ = scene_ray_cast(
                origin=obj.blender_obj.data.vertices[vertex_index].co + Vector([0., 0., 0.0001]),
                direction=np.array([0., 0., 1.]))
            # print(hit, hit_obj.get_name())
            if hit_obj.get_name() == 'top_plane':
                face_hits_top_plane = True
                continue
        if not face_hits_top_plane:
            polygon.select = True

    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.delete(type='FACE')
    bpy.ops.object.mode_set(mode='OBJECT')

    bpy.ops.mesh.separate(type='LOOSE')
    splitted_objs = [MeshObject(active_obj) for active_obj in bpy.context.selected_objects]
    bpy.ops.object.select_all(action='DESELECT')
    for obj in splitted_objs:

        obj.select()
        bpy.context.view_layer.objects.active = obj.blender_obj

        bpy.ops.object.mode_set(mode='EDIT')  # Toggle edit mode
        bpy.ops.mesh.select_mode(type='FACE')  # Change to face selection
        bpy.ops.mesh.select_all(action='DESELECT')  # Select all faces
        bpy.ops.object.mode_set(mode='OBJECT')

        edge_face_count = {i: 0 for i in range(len(obj.blender_obj.data.edges))}

        # Create a mapping from edge key to edge index for quick lookup
        edge_key_to_index = {edge.key: i for i, edge in enumerate(obj.blender_obj.data.edges)}

        # Iterate over each face in the mesh
        for face in obj.blender_obj.data.polygons:
            for edge_key in face.edge_keys:
                edge_index = edge_key_to_index[edge_key]
                edge_face_count[edge_index] += 1

        ##### step 3.2: down-project vertices, add vertices, edges and a face
        faces = obj.blender_obj.data.polygons

        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type='VERT')  # Change to face selection
        bpy.ops.mesh.select_all(action='DESELECT')  # deselect all faces
        bm = obj.mesh_as_bmesh()

        for edge in tqdm(obj.blender_obj.data.edges):
            if edge_face_count[edge.index] == 1:  # Edge is part of only one face
                bm.verts.ensure_lookup_table()
                co = bm.verts[edge.vertices[0]].co
                v0_extr = bm.verts.new([co[0], co[1], -1.])
                bmesh.update_edit_mesh(obj.blender_obj.data)
                bm.verts.ensure_lookup_table()
                bm.edges.new([bm.verts[edge.vertices[0]], v0_extr])
                bmesh.update_edit_mesh(obj.blender_obj.data)
                co = obj.blender_obj.data.vertices[edge.vertices[1]].co
                v1_extr = bm.verts.new([co[0], co[1], -1.])
                bm.verts.ensure_lookup_table()
                bm.edges.new([bm.verts[edge.vertices[1]], v1_extr])
                bmesh.update_edit_mesh(obj.blender_obj.data)
                bm.verts.ensure_lookup_table()
                bm.edges.new([v0_extr, v1_extr])
                bmesh.update_edit_mesh(obj.blender_obj.data)
                bm.verts.ensure_lookup_table()
                face = bmesh.ops.contextual_create(bm, geom=[bm.verts[edge.vertices[0]], v0_extr, v1_extr,
                                                             bm.verts[edge.vertices[1]]])
                bmesh.update_edit_mesh(obj.blender_obj.data)
                # todo raise error when edge has 0 / 3+ faces?!

    ### step 3.3: add some boolean modifiers to make the meshes closed
    bpy.ops.object.mode_set(mode='OBJECT')
    splitted_objs[0].select()
    for i, obj in enumerate(splitted_objs[1:]):
        bpy.ops.object.select_all(action='DESELECT')
        # obj.select()
        boolean_modifier(obj=splitted_objs[0], target=obj, name=f'boolean_union_with_plane_{i}', operation='UNION')
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        obj.delete()

    bpy.ops.object.select_all(action='DESELECT')
    obj = splitted_objs[0]
    obj.select()
    boolean_modifier(obj=obj, target=bot_plane, name='bot_plane', operation='UNION')

    ## step 3.4: add a cube, and subtract all splitted objects from it
    bpy.ops.object.select_all(action='DESELECT')
    cube = bproc.object.create_primitive("CUBE")
    cube.set_name('fixture')

    cube.blender_obj.dimensions = [fixture_dims[0], fixture_dims[1], z_loc[1] - z_loc[0]]
    cube.set_location([fixture_loc[0], fixture_loc[1], (z_loc[1] + z_loc[0]) / 2])

    boolean_modifier(obj=cube, target=obj, name=f'boolean_fixture', operation='DIFFERENCE')
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    # obj.delete()
    bot_plane.delete()
    top_plane.delete()
    bpy.ops.object.select_all(action='DESELECT')
    cube.select()
    if postprocess:
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='INVERT')
        bpy.ops.mesh.select_mode(type='EDGE')
        bpy.ops.object.mode_set(mode='OBJECT')
        for face in cube.blender_obj.data.polygons:
            face.select = False
        for edge in cube.blender_obj.data.edges:
            edge.select = False
        for vertex in cube.blender_obj.data.vertices:
            vertex.select = False
        bottom_cube_vertices = []
        cube_bbox = cube.get_bound_box()
        min_bbox, max_bbox = np.min(cube_bbox, axis=0), np.max(cube_bbox, axis=0)
        for vertex in cube.blender_obj.data.vertices:
            if vertex.co[0] in [min_bbox[0], max_bbox[0]] and vertex.co[1] in [min_bbox[1], max_bbox[1]] and vertex.co[2] == \
                    min_bbox[2]:
                bottom_cube_vertices.append(vertex.index)

        encaps_edges = []

        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type='FACE')
        bpy.ops.object.mode_set(mode='OBJECT')
        for face in cube.blender_obj.data.polygons:
            for (vert_idx0, vert_idx1) in face.edge_keys:
                if vert_idx0 in bottom_cube_vertices or vert_idx1 in bottom_cube_vertices:
                    encaps_edges.append(face)
                    face.select = True
                    continue
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type='FACE')
        bpy.ops.object.mode_set(mode='OBJECT')

        rem_bot_edges = []
        for edge in cube.blender_obj.data.edges:
            if not edge.select:
                v_idx0, v_idx1 = edge.key
                if cube.blender_obj.data.vertices[v_idx0].co[-1] == min_bbox[-1] and \
                        cube.blender_obj.data.vertices[v_idx1].co[-1] == min_bbox[-1]:
                    rem_bot_edges.append(edge.key)

        # deselect all, select faces which share these edges, and delete the faces
        for face in cube.blender_obj.data.polygons:
            face.select = False
        for edge in cube.blender_obj.data.edges:
            edge.select = False
        for vertex in cube.blender_obj.data.vertices:
            vertex.select = False

        faces_to_delete = []
        for face in cube.blender_obj.data.polygons:
            for edge_key in face.edge_keys:
                if edge_key in rem_bot_edges:
                    faces_to_delete.append(face)
                    continue
        print(rem_bot_edges)
        for face in faces_to_delete:
            face.select = True
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.delete(type='FACE')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.fill_holes()
        bpy.ops.object.mode_set(mode='OBJECT')
    obj2tag_trafo = add_tag_bevel(fixture=cube, tag_loc=[fixture_loc[0], fixture_loc[1], z_loc[1]], obj_mat=obj_mat,
                                  add_cube=add_cube, tag_border=tag_border)

    print('mat', obj_mat)
    return cube, obj2tag_trafo
