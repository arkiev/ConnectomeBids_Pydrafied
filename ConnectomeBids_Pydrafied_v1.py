import os
import typing as ty
import pydra  
from pydra import Workflow
from pydra.engine.specs import File
from pydra.tasks.mrtrix3.v3_0 import mrconvert, dwidenoise, mrdegibbs
from fileformats.medimage import NiftiGzXBvec, NiftiGz
from fileformats.medimage_mrtrix3 import ImageFormat

# Define the path and output_path variables
output_path = '/Users/arkievdsouza/git/ConnectomeBids_Pydrafied/outputs/'

# Define the input_spec for the workflow
input_spec = {"dwi": NiftiGz, "bvec": File, "bval": File, "json": File}
output_spec = {"dwi_convert_denoise_unring": File}

@pydra.mark.task
def merge_grads(bvec: File, bval: File) -> ty.List[File]:
    return [bvec, bval]

# Create a workflow and add the mrconvert task
wf = Workflow(name='connectomebids_carriage1_wf', input_spec=input_spec, cache_dir=output_path) 

wf.add(
    merge_grads(
        bvec=wf.lzin.bvec,
        bval=wf.lzin.bval,
        name="merge_grads",
    )
)

# Convert to mif 
wf.add(
    mrconvert(
        input=wf.lzin.dwi,
        output="dwi.mif",
        name="convert_DWI",
        fslgrad=wf.merge_grads.lzout.out,
        json_import=wf.lzin.json
    )
)

# Apply dwidenoise
wf.add(
    dwidenoise(
        name="denoise_node",
        dwi=wf.convert_DWI.lzout.output, 
        out="denoised.mif", 
        rank="rank.mif",
        noise="noise.mif" #, mask=wf.mask_node.lzout.output.cast(MrtrixImage)  
    )
)

wf.add(
    mrdegibbs(
        name="degibbs_node",
        in_=wf.denoise_node.lzout.out, 
        out="denoised_degibbs.mif", 
        nshifts=50,
    )
)

wf.set_output(("carriage1_output", wf.degibbs_node.lzout.out))

# Execute the workflow
result = wf(
    dwi="/Users/arkievdsouza/Desktop/ConnectomeBids/data/sub-01/dwi/sub-01_dir-1_dwi.nii.gz",
    bvec="/Users/arkievdsouza/Desktop/ConnectomeBids/data/sub-01/dwi/sub-01_dir-1_dwi.bvec",
    bval="/Users/arkievdsouza/Desktop/ConnectomeBids/data/sub-01/dwi/sub-01_dir-1_dwi.bval",
    json="/Users/arkievdsouza/Desktop/ConnectomeBids/data/sub-01/dwi/sub-01_dir-1_dwi.json",
    plugin="serial",
)
