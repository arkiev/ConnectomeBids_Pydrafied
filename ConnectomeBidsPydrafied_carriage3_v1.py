from ast import alias
import os
import typing as ty
import pydra  
from pydra import Workflow
from pydra.engine.specs import File
from pydra.tasks.mrtrix3.v3_0 import mrconvert, mrgrid, dwi2mask_legacy, mrmath, mrthreshold, mrinfo, dwibiasnormmask
from fileformats.medimage import NiftiGzXBvec, NiftiGz
from fileformats.medimage_mrtrix3 import ImageFormat
from pathlib import Path

# Define the path and output_path variables
output_path = '/Users/arkievdsouza/git/ConnectomeBids_Pydrafied/outputs/carriage3/'
# alias mri_synthstrip="python /Users/arkievdsouza/synthstrip-docker"

@pydra.mark.task
def run_mri_synthstrip():
    import subprocess
    # Define the command to execute
    command = ["python", "/Users/arkievdsouza/synthstrip-docker"]
    # Execute the command
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # Check if the command executed successfully
    if result.returncode != 0:
        # Print error message if the command failed
        print("Error running mri_synthstrip:")
        print(result.stderr.decode())
    # Return the stdout output
    return result.stdout.decode()

# Define the input_spec for the workflow
input_spec = {"dwi_preproc_mif": File}
output_spec = {"dwi_tmp": File}

# Create a workflow 
wf = Workflow(name='connectomebids_carriage3_wf', input_spec=input_spec, cache_dir=output_path, output_spec=output_spec) 
# wf.add(run_mri_synthstrip())

# Step 4: Generate an image containing all voxels where the DWI contains valid data
# this step can be removed since the output is used in the iterative masking process (which is no long necessary)

# wf.add(
#     mrmath(
#         input=wf.lzin.dwi_preproc_mif,
#         output="dwi_mrmath_tmp.mif",
#         name="mrmath_max_task",
#         operation="max",
#         axis=3,

#     )
# )

# wf.add(
#     mrthreshold(
#         input=wf.mrmath_max_task.lzout.output,
#         output="dwi_validdata_image.mif",
#         name="mrthreshold_task",
#         abs=0.0,
#         axis=3,
#         comparison="gt"
        
#     )
# )

# REVISIT THIS Determine whether we are working with single-shell or multi-shell data
# wf.add(
#     mrinfo(
#         image=wf.lzin.dwi_preproc_mif,
#         name="mrinfo_bvals_task",
#         shell_bvalues=True,
#     )
# )

# Step 5: create mask. no need to re-write the iterative process that has been written in connectomebids - just use dwibiasnormmask (which does the same thing)
# mri_synthstrip is a hurdle. use dwi2mask in interim 
wf.add(
    dwibiasnormmask(
        input=wf.lzin.dwi_preproc_mif,
        name="dwibiasnormmask_task",
        output_dwi="dwi_biasnorm.mif",
        output_mask="dwi_mask.mif",
        mask_algo="threshold",
        output_bias="bias_field.mif", 
        output_tissuesum="tissue_sum.mif"      
    )
)

# Step 7: Crop images to reduce storage space (but leave some padding on the sides)
#grid DWI
wf.add(
    mrgrid(
        input=wf.dwibiasnormmask_task.lzout.output_dwi, 
        name="crop_task_dwi",
        operation="crop",
        output="dwi_crop.mif",
        mask=wf.dwibiasnormmask_task.lzout.output_mask,
        uniform=-3,
    )
)

#grid dwimask
wf.add(
    mrgrid(
        input=wf.dwibiasnormmask_task.lzout.output_mask, 
        name="crop_task_mask",
        operation="crop",
        output="mask_crop.mif",
        mask=wf.dwibiasnormmask_task.lzout.output_mask,
        uniform=-3,
    )
)

# REPLACE Step8-10 with epi_reg (and transform DWI to T1 space)

# Step 8: Generate target images for T1->DWI registration
# Step 9: Perform DWI->T1 registration
# Step 10: Perform DWI->T1 transformation


# wf.set_output(("carriage3_output", wf.dwibiasnormmask_task.lzout.output_dwi))
# wf.set_output(("carriage3_output", wf.crop_task_mask.lzout.output))
# wf.set_output(("carriage3_output", wf.crop_task_dwi.lzout.output))

wf.set_output(("carriage3_output", wf.dwibiasnormmask_task.lzout.output_dwi))

# ########################
# # Execute the workflow #
# ########################

# wf = connectomebids_carriage3_wf(direction=direction)
result = wf(dwi_preproc_mif="/Users/arkievdsouza/Desktop/ConnectomeBids/output/MRtrix3_connectome-preproc/sub-01/dwi/sub-01_desc-preproc_dwi.mif.gz",
    # T1_image="/Users/arkievdsouza/Desktop/ConnectomeBids/data/sub-01/anat/sub-01_T1w.nii.gz",
    plugin="serial",
)
