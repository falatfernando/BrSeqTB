# Development & Execution Workflow — BrSeqTB

**Document ID**: `DEV-001`  
**Repository**: `LaPAM-USP/BrSeqTB`  
**Date**: August 13, 2026  
**Pipeline Framework**: Nextflow DSL2  

---

## 1. System Setup & Installation

### 1.1 Prerequisites
Before installing BrSeqTB, the following system-level tools must be available:
- **Linux** (x86_64) or **macOS**.
- **Java OpenJDK 17**: Required by Nextflow and GATK/Picard/SnpEff.
- **Nextflow** ($\ge 25.10.2$).
- **Miniconda / Mamba**: Used by Nextflow to automatically instantiate the Conda environment defined in [envs/brseqtb.yml](file:///home/falat/Repositories/BrSeqTB/envs/brseqtb.yml).

### 1.2 Installation Steps
```bash
# 1. Clone the repository
git clone https://github.com/LaPAM-USP/BrSeqTB.git
cd BrSeqTB

# 2. Run the installer script
bash install.sh

# 3. Source environment
source ~/.bashrc
```
The [install.sh](file:///home/falat/Repositories/BrSeqTB/install.sh) script verifies Java and Nextflow, sets execute permissions on `bin/brseqtb`, and appends `export PATH="<REPO>/bin:$PATH"` to `~/.bashrc`.

### 1.3 Conda Terms of Service Requirement
Recent Conda versions require pre-acceptance of Anaconda channel terms of service for non-interactive environment creation:
```bash
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r
```

---

## 2. Configuration & Parameterization

Execution settings can be adjusted via CLI flags or by editing [nextflow.config](file:///home/falat/Repositories/BrSeqTB/nextflow.config).

### 2.1 Sample Sheet Preparation
Prepare `input/input_table.csv` (or `input/input_table.xlsx`) containing at minimum the `Biosample` column:
```csv
Biosample,Requisição - Request ID,Paciente - Patient Name,...
1827-22,REQ-1001,Patient Alpha,...
```

### 2.2 FASTQ Staging
Place paired FASTQ files in `reads/` using either:
- **Illumina Standard**: `1827-22_S1_L001_R1_001.fastq.gz` and `1827-22_S1_L001_R2_001.fastq.gz`.
- **Simplified Convention**: `1827-22_1.fastq.gz` and `1827-22_2.fastq.gz` (requires `--readsNaming simplified`).

---

## 3. Running the Pipeline

### 3.1 Full Pipeline Execution
```bash
# Run with default settings (local auto-scaled resources)
brseqtb

# Run with simplified naming
brseqtb --readsNaming simplified

# Run with low-memory profile (8GB RAM laptops)
brseqtb -profile lowmem

# Run on SLURM HPC cluster
brseqtb -profile hpc
```

### 3.2 Single Module Execution (`--module`)
To run a single module in isolation:
```bash
brseqtb --module fastqc
brseqtb --module trimmomatic
brseqtb --module bwa
brseqtb --module lofreq --lofreqMinAf 0.10
```
> [!IMPORTANT]
> When executing isolated modules with `--module`, prerequisite input files from upstream steps must already exist in the corresponding root-level folders (e.g. `bwa` requires trimmed reads in `trimmomatic/<sample>/`). Nextflow will not automatically execute missing upstream steps in `--module` mode.

### 3.3 Module Exclusion (`--exclude`)
To exclude optional modules during a full pipeline run:
```bash
brseqtb --exclude kaiju
brseqtb --exclude transmission,iqtree
brseqtb --exclude clinical_report
```

---

## 4. Output Verification & Deliverables

Outputs are written to the following destinations:
- **Clinical Reports**: `results/clinicalReport/<biosample>.docx`
- **Curated Resistance Reports**: `results/resistance/<biosample>.xlsx`
- **Cohort Resistance Summary**: `results/resistance_summary.xlsx`
- **Master QC Summary**: `results/qc_summary.xlsx`
- **Phylogenetic Trees & Clusters**: `iqtree/snpmatrix.treefile`, `results/transmission_clusters.csv`
- **Runtime Logs & Traces**: `logs/trace.txt`, `logs/timeline.html`, `logs/report.html`, `logs/dag.html`

---

## 5. Testing & Quality Assurance

### 5.1 Current Repository Status
- The [tests/](file:///home/falat/Repositories/BrSeqTB/tests) directory is empty.
- There are no automated unit tests, integration tests, or end-to-end CI workflows.

### 5.2 Manual Verification Procedure
A developer currently validates changes by executing standalone script runs on test data:
```bash
# 1. Test sample validation
python bin/make_manifest_validate.py --table input/input_table.csv --reads reads --out manifest.tsv

# 2. Test WHO catalogue parsing
python bin/omsCatalog.py

# 3. Test single-sample lineage typing (requires normalized VCF)
python bin/lineage.py <biosample>
```

---

## 6. Debugging & Troubleshooting

### 6.1 Inspecting Intermediate Outputs
Because processes write directly into project root directories rather than isolated task directories:
1. Inspect individual process log files (e.g., `fastqc/<sample>/<sample>_fastqc_summary.csv`, `bwa/<sample>/tmp/<sample>_flagstat.txt`, `lofreq/<sample>/<sample>_lofreq.raw.vcf`).
2. Review Nextflow log output in `.nextflow.log` and execution trace in `logs/trace.txt`.

### 6.2 Cleaning Workflow State
To reset the workflow state:
```bash
# Clear Nextflow task cache
nextflow clean -f
rm -rf work/ .nextflow/

# To re-run stages from scratch, remove generated root-level directories
rm -rf fastqc/ trimmomatic/ bwa/ delly/ lofreq/ gatk/ norm/ snpeff/ cohort/ snpMatrix/ transmission/ iqtree/ mixInfection/ resistance/ results/
```
