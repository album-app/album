---
args:
- action: !!python/name:hips.deploy.%3Clambda%3E ''
  default: /mnt/data/RadialSymmetry/ImagesForStephan/Empty_Bg_SNR_Range_Sigxy_1_SigZ_2/Poiss_30spots_bg_200_16_I_300_0_img0.tif
  description: Path to a 2D or 3D image stack
  name: imp
- action: !!python/name:hips.deploy.%3Clambda%3E ''
  default: 1.0
  description: Anisotropy of voxels in the 3D image
  name: anisotropy
- action: !!python/name:hips.deploy.%3Clambda%3E ''
  default: true
  description: Use RANSAC
  name: RANSAC
- action: !!python/name:hips.deploy.%3Clambda%3E ''
  default: 2.0
  description: Sigma value for radial symmetry
  name: sigma
- action: !!python/name:hips.deploy.%3Clambda%3E ''
  default: 0.01
  description: Threshold for radial symmetry
  name: threshold
- action: !!python/name:hips.deploy.%3Clambda%3E ''
  default: 1
  description: Support region around the point for radial symmetry
  name: supportRegion
- action: !!python/name:hips.deploy.%3Clambda%3E ''
  default: 0.3
  description: Inlier ratio for determining points
  name: inlierRatio
- action: !!python/name:hips.deploy.%3Clambda%3E ''
  default: 0.75
  description: Maximum error
  name: maxError
- action: !!python/name:hips.deploy.%3Clambda%3E ''
  default: ./radial_symmetry_results.txt
  description: Results file for saving all detected points
  name: resultsPath
authors: Specification Author XY
cite: radial symmetry paper <3
covers:
- /assets/images/solutions/radial-symmetry/cover.png
description: Radial symmetry HIP Solution
documentation: ''
doi: coming soon
format_version: 0.3.0
git_repo: https://github.com/ida-mdc/hips
license: MIT License
min_hips_version: 0.1.0
name: radial-symmetry
sample_inputs:
- /assets/images/solutions/radial-symmetry/radial_symmetry_example_input.tif
sample_outputs:
- /assets/images/solutions/radial-symmetry/radial_symmetry_example_result.txt
tags:
- point detection
tested_hips_version: 0.1.0
timestamp: '2021-02-08T22:16:03.331998'
version: 0.1.0

---