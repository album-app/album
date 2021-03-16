def resolve_hips(hips_dependency):
    """Resolves a hips id and returns a path to the solution file."""
    # TODO properly implement this - i.e. match with zenodo
    catalog = "/home/random/Development/hips/repos/hips-catalog"
    if hips_dependency["group"] == "ida-mdc" and hips_dependency["name"] == "blender":
        return "%s/solutions/blender.py" % catalog
    if hips_dependency["group"] == "ida-mdc" and hips_dependency["name"] == "sciview-volume-rendering":
        return "%s/solutions/sciview_volume_rendering.py" % catalog
    if hips_dependency["group"] == "ida-mdc" and hips_dependency["name"] == "sciview-labels-to-mesh":
        return "%s/solutions/sciview_labels_to_mesh.py" % catalog
    if hips_dependency["group"] == "ida-mdc" and hips_dependency["name"] == "otsu-segmentation":
        return "%s/solutions/otsu_segmentation.py" % catalog
    if hips_dependency["group"] == "ida-mdc" and hips_dependency["name"] == "blender-render":
        return "%s/solutions/blender_render.py" % catalog
    if hips_dependency["group"] == "ida-mdc" and hips_dependency["name"] == "blender-import-meshes":
        return "%s/solutions/blender_import_meshes.py" % catalog
    raise RuntimeError(f"Cannot find {hips_dependency}.")

