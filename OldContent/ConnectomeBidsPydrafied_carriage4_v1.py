from ast import alias
import os
import typing as ty
import pydra  
from pydra import Workflow
from pydra.engine.specs import File
from pydra.tasks.mrtrix3.v3_0 import mrconvert, mrgrid,dwi2mask_legacy, mrmath, mrthreshold,mrinfo, dwibiasnormmask
from fileformats.medimage import NiftiGzXBvec, NiftiGz
from fileformats.medimage_mrtrix3 import ImageFormat
from pathlib import Path

# Define the path and output_path variables
output_path = '/Users/arkievdsouza/git/ConnectomeBids_Pydrafied/outputs/carriage4/'

# Define the input_spec for the workflow
input_spec = {"dwi_preproc_mif": File}
output_spec = {"dwi_tmp": File}

# Create a workflow 
wf = Workflow(name='connectomebids_carriage4_wf', input_spec=input_spec, cache_dir=output_path, output_spec=output_spec)

wf.set_output(("carriage4_output", wf.crop_task_dwi.lzout.output))

# ########################
# # Execute the workflow #
# ########################

result = wf(
    dwi_preproc_mif="/Users/arkievdsouza/Desktop/ConnectomeBids/output/MRtrix3_connectome-preproc/sub-01/dwi/sub-01_desc-preproc_dwi.mif.gz",
    T1_image="/Users/arkievdsouza/Desktop/ConnectomeBids/data/sub-01/anat/sub-01_T1w.nii.gz",
    plugin="serial",
)
