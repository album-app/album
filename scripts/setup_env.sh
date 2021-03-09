# Purge and install a fresh hips conda environment including installing hips from pip

conda env remove -n hips
conda env create -f hips.yml
eval "$(conda shell.bash hook)"
conda activate hips
pip install -e .
