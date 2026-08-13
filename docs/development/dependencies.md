# Dependency Map & Software Inventory — BrSeqTB

**Document ID**: `DEP-001`  
**Repository**: `LaPAM-USP/BrSeqTB`  
**Date**: August 13, 2026  
**Pipeline Framework**: Nextflow DSL2  

---

## 1. Software & Environment Dependencies

The pipeline execution environment is defined in [envs/brseqtb.yml](file:///home/falat/Repositories/BrSeqTB/envs/brseqtb.yml).

### 1.1 Core Execution & Scripting Environment

| Dependency | Version | Type | Purpose | Where Defined | Where Used | Version Pinned? | Reproducibility Impact | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Nextflow** | `>=25.10.2` | Workflow Engine | Workflow execution & DAG scheduling | Host runtime | CLI entry point (`brseqtb`, `main.nf`) | No (Range) | High | Requires DSL2 support |
| **Java OpenJDK** | `17` | Runtime Engine | Runtime for Nextflow, GATK4, Picard, SnpEff | `envs/brseqtb.yml:44` | System / Tools | Yes (`17`) | High | Required by GATK4 & Nextflow |
| **Python** | `3.10` | Interpreter | Script execution & analytical logic | `envs/brseqtb.yml:14` | All `bin/*.py` scripts | Yes (`3.10`) | High | Pinned to ensure C-extension compatibility |
| **Bash** | `>=4.0` | Shell | Module script wrapper execution | Host system | All `bin/*.sh` scripts | No | Medium | Relies on `-euo pipefail` |
| **bc** | Latest | System Tool | Floating-point arithmetic calculations in shell | `envs/brseqtb.yml:16` | `fastqc.sh`, `trimmomatic.sh`, `bwa.sh`, `ntmFilter.sh` | No | Low | Standard CLI utility |
| **pigz / parallel**| Latest | System Tool | Multithreaded compression & execution | `envs/brseqtb.yml:20-21`| Runtime support | No | Low | Acceleration tools |

---

### 1.2 Bioinformatics Tools Matrix

| Tool | Version in Conda | Type | Purpose | Where Defined | Where Used | Version Pinned? | Reproducibility Impact | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **BWA** | `0.7.17` | Binary | Short-read alignment to H37Rv | `envs/brseqtb.yml:26` | `bin/bwaref.sh`, `bin/bwa.sh` | Yes (`0.7.17`) | High | Canonical Burrows-Wheeler aligner |
| **SAMtools** | `1.18` | Binary | BAM sorting, indexing, flagstat, faidx | `envs/brseqtb.yml:27` | `bin/bwa.sh`, `bin/gatkdict.sh`, `bin/lofreq.sh` | Yes (`1.18`) | High | Core HTS library binary |
| **BCFtools** | `1.18` | Binary | VCF/BCF querying, indexing, norm | `envs/brseqtb.yml:28` | `bin/delly.sh`, `bin/norm.sh`, `bin/ntmFilter.sh` | Yes (`1.18`) | High | Core variant manipulation tool |
| **HTSlib** | `1.18` | Binary | Bgzip compression and tabix indexing | `envs/brseqtb.yml:29-30`| `bin/delly.sh`, `bin/norm.sh`, `bin/snpeff.sh` | Yes (`1.18`) | High | Companion library for BAM/VCF indexing |
| **GATK4** | `4.x` (Unpinned) | Java / Binary | HaplotypeCaller, GenomicsDB, GenotypeGVCFs | `envs/brseqtb.yml:35` | `bin/gatkdict.sh`, `bin/gatkGvcf.sh`, `bin/gatkVcf.sh`, `bin/cohort.sh` | No | High | Major caller; unpinned version risks minor variant call shifts |
| **Picard** | `3.x` (Unpinned) | Java / Binary | Optical duplicate marking (`MarkDuplicates`) | `envs/brseqtb.yml:36` | `bin/bwa.sh` | No | Medium | Uses `LENIENT` validation stringency |
| **Delly** | `1.x` (Unpinned) | Binary | Structural variant discovery | `envs/brseqtb.yml:37` | `bin/delly.sh` | No | Medium | Structural variant caller |
| **LoFreq** | `2.1.x` (Unpinned)| Binary | Low-frequency somatic variant detection | `envs/brseqtb.yml:38` | `bin/lofreq.sh` | No | High | Requires `indelqual` calibration |
| **vt** | `2015.11.10` | Binary | Block substitution decomposition | `envs/brseqtb.yml:39` | `bin/norm.sh` | Yes (`2015.11.10`) | High | Normalizes complex multi-nucleotide changes |
| **SnpEff** | `5.2` | Java / Binary | Functional variant impact prediction | `envs/brseqtb.yml:45` | `bin/snpeffdb.sh`, `bin/snpeff.sh` | Yes (`5.2`) | High | Builds custom `NC_0009623` database |
| **FastQC** | `0.12.x` (Unpinned)| Java / Binary | Raw read quality analysis | `envs/brseqtb.yml:50` | `bin/fastqc.sh` | No | Low | Standard read QC utility |
| **Trimmomatic** | `0.39` (Unpinned) | Java / Binary | Quality trimming & read length filtering | `envs/brseqtb.yml:51` | `bin/trimmomatic.sh` | No | Medium | Sliding window 4:20, minlen 50 |
| **IQ-TREE** | `2.x` (Unpinned) | Binary | Maximum Likelihood phylogenetic tree inference | `envs/brseqtb.yml:52` | `bin/iqtree.sh` | No | High | Model `HKY+I+G` with 1000 ultrafast bootstraps |
| **Kaiju** | `1.9.x` (Unpinned)| Binary | Taxonomic read classification | `envs/brseqtb.yml:53` | `bin/kaijudb.sh`, `bin/kaiju.sh` | No | High | Exact protein k-mer match on FM-index |
| **Krona** | `2.8.x` (Unpinned)| Perl / Binary | Hierarchical taxonomic visualization | `envs/brseqtb.yml:54` | `bin/kaiju.sh` | No | Low | Renders HTML Krona charts |

---

### 1.3 Python Scientific Stack

| Package | Imported Module | Purpose | Where Used | Version Pinned? | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **numpy** | `numpy` | Array manipulations, coordinate arithmetic | `omsCatalog.py`, `tbdrRCov.py` | No | In `envs/brseqtb.yml:59` |
| **pandas** | `pandas` | Manifest processing, WHO catalogue filtering, QC & AMR table generation | `omsCatalog.py`, `tbdrRCov.py`, `cohortFilter.py`, `transmission.py`, `resistanceTarget.py`, `resistanceReport.py`, `resistanceSummary.py`, `qcSummary.py`, `clinicalReport.py` | No | In `envs/brseqtb.yml:60` |
| **networkx**| `networkx` | Pairwise SNP graph construction & MST clustering | `transmission.py` | No | In `envs/brseqtb.yml:61` |
| **biopython**| `Bio.SeqIO` | FASTA alignment reading & genome modification | `snpMatrix.py`, `transmission.py` | No | In `envs/brseqtb.yml:62` |
| **pysam** | `pysam` | Indexed BAM coverage parsing and VCF record extraction | `tbdrRCov.py`, `snpMatrix.py`, `resistanceTarget.py` | No | In `envs/brseqtb.yml:63` |
| **openpyxl**| `openpyxl` | Ingestion of XLSX sample sheets & WHO catalogue | `make_manifest_validate.py`, `omsCatalog.py`, `cohortFilter.py`, `resistanceTarget.py`, `resistanceReport.py`, `resistanceSummary.py`, `qcSummary.py`, `clinicalReport.py` | No | In `envs/brseqtb.yml:64` |
| **xlsxwriter**| `xlsxwriter` | Multi-sheet Excel workbook export | `qcSummary.py` | No | In `envs/brseqtb.yml:65` |
| **python-docx**| `docx` | Microsoft Word clinical report generation from template | `clinicalReport.py` | No | In `envs/brseqtb.yml:66` |

---

## 2. Biological & Reference Dependencies

| Resource Name | Source / Origin | Version / Date | Location in Repo | Where Used | Pinned / Static? | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **H37Rv Reference Genome** | NCBI RefSeq (`NC_000962.3`) | Complete (4,411,532 bp) | `database/mtbRef/NC0009623.fasta` | `bwa.sh`, `gatkdict.sh`, `gatkGvcf.sh`, `gatkVcf.sh`, `norm.sh`, `cohort.sh`, `snpMatrix.py` | Static File | Canonical reference sequence |
| **H37Rv Gene Annotations** | NCBI RefSeq (`NC_000962.3`) | GFF3 feature format | `database/mtbRef/genes.gff` | `bin/snpeffdb.sh` | Static File | Annotations used for SnpEff DB build |
| **Forbidden Genes List** | Curated literature list | 488 gene IDs | `database/mtbRef/forbidden_genes.txt` | `bin/snpMatrix.py` | Static File | Excludes PE/PPE & mobile elements |
| **WHO TB Resistance Catalogue** | World Health Organization | 2023 2nd Edition (`v2023.7`) | `database/omsCatalog/WHO-UCN-TB-2023.7-eng.xlsx` | `bin/omsCatalog.py` | Static File (30.9 MB) | Core AMR association standard |
| **Kaiju Custom Database** | Zenodo archive | Record `18064127` | `database/kaiju/db/` | `bin/kaijudb.sh`, `bin/kaiju.sh` | Remote Archive (SHA256 verified) | Downloaded at runtime by `kaijudb.sh` |
| **Embedded Lineage Markers** | In-code dictionary (`BrSeq_db`) | 5,760 dictionary rows | `bin/lineage.py:23-5640` | `bin/lineage.py` | Static In-Code | Hardcoded SNP database |
| **Auxiliary Cohort Isolates** | NCBI SRA (9 isolates) | Precomputed VCFs & gVCFs | `assets/auxCohort/gatk/` | `bin/cohort.sh` | Static Files | SRR34768817 to SRR34768879 |
| **Clinical Report Template** | Custom DOCX design | Word 2016+ template | `assets/templates/report_template.docx` | `bin/clinicalReport.py` | Static File | Pre-styled report layout |
| **Clinical Translation Dictionary**| Missing dependency | Unknown | `database/omsCatalog/dictionary.xlsx` | `bin/clinicalReport.py:49` | **MISSING** | Missing file; handled by try/except |
