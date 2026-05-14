# Methylong Document

# 工具文档: methylong: Output

##  nf-core/methylong

[ __Edit](https://github.com/nf-core/methylong/blob/2.0.0/docs/output.md "Edit this page on GitHub")

Extract methylation calls from long reads (ONT/ PacBio)

dna-methylationfiber-seqlong-readontpacbio

[ __Launch version 2.0.0](/launch/?pipeline=methylong&release=2.0.0) [ __https://github.com/nf-core/methylong](https://github.com/nf-core/methylong/tree/2.0.0)

  * [ __Introduction](/methylong/2.0.0/ "introduction")
  * [ __Usage](/methylong/2.0.0/docs/usage/ "usage")
  * [ __Parameters](/methylong/2.0.0/parameters/ "parameters")
  * [ __Output](/methylong/2.0.0/docs/output/ "output")
  * [ __Results](/methylong/2.0.0/results/methylong/results-3513e80df682ad20f42d6429a2ee142b606949b5/ "results")
  * [ __Releases](/methylong/releases_stats/ "releases")
  * __

2.0.0 
    * [ 2.0.0 ](/methylong/2.0.0/docs/output)
    * [ 1.0.0 ](/methylong/1.0.0/docs/output)
    * [ dev ](/methylong/dev/docs/output)

__Output

[ __Introduction](/methylong/2.0.0/)[ __Usage](/methylong/2.0.0/docs/usage/)[ __Parameters](/methylong/2.0.0/parameters/)[ __Output](/methylong/2.0.0/docs/output/)[ __Results](/methylong/2.0.0/results/methylong/results-3513e80df682ad20f42d6429a2ee142b606949b5/)[ __Releases](/methylong/releases_stats/)

__

2.0.0 

  * [ 2.0.0 ](/methylong/2.0.0/docs/output)
  * [ 1.0.0 ](/methylong/1.0.0/docs/output)
  * [ dev ](/methylong/dev/docs/output)

### Introduction __

This document describes the output produced by the pipeline.

The directories listed below will be created in the results directory after the pipeline has finished. All paths are relative to the top-level results directory.

### Pipeline overview __

The pipeline is built using [Nextflow](https://www.nextflow.io/) and processes data using the following steps:

  * FastQC \- Raw read QC
  * Modcalling \- basecall and modcall
  * Preprocessing reads \- Adapters and Barcodes removal
  * Alignment \- alignment to reference genome
  * Methylation calling \- pile up of methylation calls
  * Bed to bedgraph conversion \- convert bed to bedgraph
  * SNV calling \- germline small variant calls
  * Phasing \- phase genomic variant
  * DMR analysis \- DMR results
  * Fiberseq \- fiberseq results
  * MultiQC \- Aggregate report describing triming and alignment results and QC from the whole pipeline
  * Pipeline information \- Report metrics generated during the workflow execution

#### FastQC __

Output files

  * `fastqc/`
    * `*_fastqc.html`: FastQC report containing quality metrics.
    * `*_fastqc.zip`: Zip archive containing the FastQC report, tab-delimited data file and plot images.

[FastQC](http://www.bioinformatics.babraham.ac.uk/projects/fastqc/) gives general quality metrics about your sequenced reads. It provides information about the quality score distribution across your reads, per base sequence content (%A/T/G/C), adapter contamination and overrepresented sequences. For further reading and documentation see the [FastQC help pages](http://www.bioinformatics.babraham.ac.uk/projects/fastqc/Help/).

#### Modcalling __

Modification calling (`modcalling`) includes basecall for ONT pod5 reads and modcall.

Output files

  * `basecall/`
    * `*_calls.bam`: reads after basecalling.
  * `modcall/`
    * `*_modbam.bam`: reads after modcalling with MM/ML tags, if pacbio_modcaller is jasmine.
    * `*_ccsmeth_modbam.bam`: reads after modcalling with MM/ML tags, if pacbio_modcaller is ccsmeth.

#### Preprocessing reads __

Preprocessing of reads are only available for ONT reads. Reads are trimmed, then MM/ML tags are repaired.

Output files

  * `trim/`
    * `*_fastq.gz`: reads after trimming.
    * `*.log`: trimming log
  * `repair/`
    * `*_repaired.bam`: reads after repairing MM/ML tags.
    * `*_repaired.log`: repair log

#### Alignment __

Output files

  * `alignment/`
    * `*.bam`: aligned modBAM.
    * `*.bam.bai`: alignment index
    * `*.flagstat`: alignment summary

#### Pileup __

Methylation pile up for PacBio data can be preformed by either modkit or pb-CpG-tools.

Output files

##### modkit output:__

  * `pileup/`
    * `*.bed.gz`: pileup of methylation calls in compressed bed format
    * `*_pileup.log`: pileup log

##### pb-CpG-tools output:__

  * `pileup/`
    * `*.bed.gz`: pileup of methylation calls in compressed bed format
    * `*_pileup.log`: pileup log
    * `*.bw`: bigwig format

#### Bedgraphs __

Output files

  * `bedgraphs/`
    * `*.bedgraph`: context specific bedgraph output

#### SNV calling __

Output files

  * `snvcall/`
    * `*.vcf.gz`: snv calls
    * `*.vcf.gz.tbi`: snv-call index
    * `*_SNV_PASS.vcf`: pass-filtered snv calls

#### Phasing __

Output files

  * `phase/`
    * `*phased.vcf`: phased vcf
    * `*.bam`: haplotagged bam
    * `*.readlist`: haplotagged readlist

#### DMR analysis __

DMR analysis includes haplotype level and population scale, and can be preformed by either DSS or modkit.

Output files

##### DSS output:__

  * `dmr_haplotype_level/dss/`
    * `*_preprocessed_<1|2|etc>.bed`: partitioned reads based on HP tag
    * `*_DSS_DMLtest.txt`: DML test results
    * `*_DSS_callDML.txt`: DML
    * `*_DSS_callDMR.txt`: DMR
    * `*_DSS.log`: DSS log

##### modkit dmr output:__

  * `dmr_haplotype_level/modkit/`

    * `*_<1|2|etc>.bed`: partitioned reads based on HP tag
    * `*_modkit_dmr_haplotype_level.bed`: differential methylation output
  * `dmr_population_scale/`

    * `*_DSS_DMLtest.txt`: DML test results
    * `*_DSS_callDML.txt`: DML
    * `*_DSS_callDMR.txt`: DMR
    * `*_DSS.log`: DSS log

#### Fiberseq __

Output files

  * `fiberseq/`
    * `*_m6a_predicted.bam`: PacBio reads after m6a calling.
    * `*_m6acall.bam`: ONT reads after m6a calling.
    * `*_m6a.bed`: pileup of m6a calls.

#### MultiQC __

Output files

  * `multiqc/`
    * `multiqc_report.html`: a standalone HTML file that can be viewed in your web browser.
    * `multiqc_data/`: directory containing parsed statistics from the different tools used in the pipeline.
    * `multiqc_plots/`: directory containing static images from the report in various formats.

[MultiQC](http://multiqc.info/) is a visualization tool that generates a single HTML report summarising all samples in your project. Most of the pipeline QC results are visualised in the report and further statistics are available in the report data directory.

Results generated by MultiQC collate pipeline QC from supported tools e.g. FastQC. The pipeline has special steps which also allow the software versions to be reported in the MultiQC output for future traceability. For more information about how to use MultiQC reports, see [http://multiqc.info](http://multiqc.info/).

#### Pipeline information __

Output files

  * `pipeline_info/`
    * Reports generated by Nextflow: `execution_report.html`, `execution_timeline.html`, `execution_trace.txt` and `pipeline_dag.dot`/`pipeline_dag.svg`.
    * Reports generated by the pipeline: `pipeline_report.html`, `pipeline_report.txt` and `software_versions.yml`. The `pipeline_report*` files will only be present if the `--email` / `--email_on_fail` parameter’s are used when running the pipeline.
    * Reformatted samplesheet files used as input to the pipeline: `samplesheet.valid.csv`.
    * Parameters used by the pipeline run: `params.json`.

[Nextflow](https://www.nextflow.io/docs/latest/tracing.html) provides excellent functionality for generating various reports relevant to the running and execution of the pipeline. This will allow you to troubleshoot errors with the running of the pipeline, and also provide you with other information such as launch commands, run times and resource usage.

**On this page**

# 工具文档: methylong: Usage

##  nf-core/methylong

[ __Edit](https://github.com/nf-core/methylong/blob/2.0.0/docs/usage.md "Edit this page on GitHub")

Extract methylation calls from long reads (ONT/ PacBio)

dna-methylationfiber-seqlong-readontpacbio

[ __Launch version 2.0.0](/launch/?pipeline=methylong&release=2.0.0) [ __https://github.com/nf-core/methylong](https://github.com/nf-core/methylong/tree/2.0.0)

  * [ __Introduction](/methylong/2.0.0/ "introduction")
  * [ __Usage](/methylong/2.0.0/docs/usage/ "usage")
  * [ __Parameters](/methylong/2.0.0/parameters/ "parameters")
  * [ __Output](/methylong/2.0.0/docs/output/ "output")
  * [ __Results](/methylong/2.0.0/results/methylong/results-3513e80df682ad20f42d6429a2ee142b606949b5/ "results")
  * [ __Releases](/methylong/releases_stats/ "releases")
  * __

2.0.0 
    * [ 2.0.0 ](/methylong/2.0.0/docs/usage)
    * [ 1.0.0 ](/methylong/1.0.0/docs/usage)
    * [ dev ](/methylong/dev/docs/usage)

__Usage

[ __Introduction](/methylong/2.0.0/)[ __Usage](/methylong/2.0.0/docs/usage/)[ __Parameters](/methylong/2.0.0/parameters/)[ __Output](/methylong/2.0.0/docs/output/)[ __Results](/methylong/2.0.0/results/methylong/results-3513e80df682ad20f42d6429a2ee142b606949b5/)[ __Releases](/methylong/releases_stats/)

__

2.0.0 

  * [ 2.0.0 ](/methylong/2.0.0/docs/usage)
  * [ 1.0.0 ](/methylong/1.0.0/docs/usage)
  * [ dev ](/methylong/dev/docs/usage)

### Introduction __

The nf-core/methylong pipeline provides long-read specific workflows for DNA methylation analysis. It supports multiple input data types, various basecallers and aligners, and includes downstream analyses such as Fiber-seq, SNV calling, haplotype phasing, and DMR analysis.

__

Loading graph

### Samplesheet input __

You will need to create a samplesheet with information about the samples you would like to analyse before running the pipeline. Use this parameter to specify its location. It has to be a comma-separated file with 5 columns, and a header row as shown in the examples below.
    
    
    --input '[path to samplesheet file]'

#### Full samplesheet __

The samplesheet required 5 columns, as defined in the table below. Sample name can be repeated if the corresponding sample has both ONT and PacBio HiFi data. One group can contain multiple samples.

samplesheet.csv
    
    
    group,sample,path,ref,method
    group1,sample1,sample1.bam,sample1.fasta,pacbio
    group2,sample2,sample2.bam,sample2.fasta,pacbio
    group3,sample3,sample3.bam,sample3.fasta,pacbio
    group3,sample3,sample3.bam,sample3.fasta,ont
    group3,sample4,sample4.bam,sample4.fasta,ont

Column| Description  
---|---  
`group`| Custom sample group name.  
`sample`| Custom sample name.  
`modbam`| Full path to modification basecalled bam file. This bam file has to be unaligned bam file. File has to have the extension “.bam”.  
`ref`| Full path to reference genome file . File can be either gzipped or not. File has to have the extension ‘.fa’, ‘.fasta’, ‘.fna’ or their equivalent gzip format.  
`method`| Sequencing method has to be specified. Either ‘ont’ or ‘pacbio’ can be accepted.  
  
An [example samplesheet](https://github.com/nf-core/methylong/blob/2.0.0/assets/test_data/test_samplesheet.csv) has been provided with the pipeline.

### Running the pipeline __

**The typical command for running the pipeline is as follows:**
    
    
    nextflow run nf-core/methylong --input ./samplesheet.csv --outdir ./results -profile docker

This will launch the pipeline with the `docker` configuration profile. See below for more information about profiles.

default workflow is:
    
    
    preprocessing (ONT) --> genome alignment --> methylation calling --> SNV calling --> haplotype phasing --> DMR calling

**Example command for PacBio unmodified BAM inputs is as follows:**
    
    
    nextflow run nf-core/methylong --input ./samplesheet_unmodified_bam.csv --outdir ./results -profile docker --pacbio_modcall

**Example command for fiberseq-m6a-calling is as follows:**
    
    
    nextflow run nf-core/methylong --input ./samplesheet_dorado.csv --outdir ./results -profile docker --dorado_modification 5mCG_5hmCG 6mA --fiberseq
    
    
    nextflow run nf-core/methylong --input ./samplesheet_pacbio.csv --outdir ./results -profile docker --fiberseq

**Example command for DMR population scale is as follows:**
    
    
    nextflow run nf-core/methylong --input ./samplesheet_dmr.csv --outdir ./results -profile docker --dmr_population_scale --dmr_a group_name_1 --dmr_b group_name_2

Note that the pipeline will create the following files in your working directory:
    
    
    work                # Directory containing the nextflow working files
    <OUTDIR>            # Finished results in specified location (defined with --outdir)
    .nextflow_log       # Log file from Nextflow
    # Other nextflow hidden files, eg. history of pipeline runs and old logs.

If you wish to repeatedly use the same parameters for multiple runs, rather than specifying each flag in the command, you can specify these in a params file.

Pipeline settings can be provided in a `yaml` or `json` file via `-params-file <file>`.

Warning

Do not use `-c <file>` to specify parameters as this will result in errors. Custom config files specified with `-c` must only be used for [tuning process resource specifications](https://nf-co.re/docs/usage/configuration#tuning-workflow-resources), other infrastructural tweaks (such as output directories), or module arguments (args).

The above pipeline run specified with a params file in yaml format:
    
    
    nextflow run nf-core/methylong -profile docker -params-file params.yaml

with:

params.yaml
    
    
    input: './samplesheet.csv'
    outdir: './results/'
    <...>

You can also generate such `YAML`/`JSON` files via [nf-core/launch](https://nf-co.re/launch).

#### Updating the pipeline __

When you run the above command, Nextflow automatically pulls the pipeline code from GitHub and stores it as a cached version. When running the pipeline after this, it will always use the cached version if available - even if the pipeline has been updated since. To make sure that you’re running the latest version of the pipeline, make sure that you regularly update the cached version of the pipeline:
    
    
    nextflow pull nf-core/methylong

#### Reproducibility __

It is a good idea to specify the pipeline version when running the pipeline on your data. This ensures that a specific version of the pipeline code and software are used when you run your pipeline. If you keep using the same tag, you’ll be running the same version of the pipeline, even if there have been changes to the code since.

First, go to the [nf-core/methylong releases page](https://github.com/nf-core/methylong/releases) and find the latest pipeline version - numeric only (eg. `1.3.1`). Then specify this when running the pipeline with `-r` (one hyphen) - eg. `-r 1.3.1`. Of course, you can switch to another version by changing the number after the `-r` flag.

This version number will be logged in reports when you run the pipeline, so that you’ll know what you used when you look back in the future. For example, at the bottom of the MultiQC reports.

To further assist in reproducibility, you can use share and reuse parameter files to repeat pipeline runs with the same settings without having to write out a command with every single parameter.

Tip

If you wish to share such profile (such as upload as supplementary material for academic publications), make sure to NOT include cluster specific paths to files, nor institutional specific profiles. 

### Core Nextflow arguments __

Note

These options are part of Nextflow and use a _single_ hyphen (pipeline parameters use a double-hyphen)

#### `-profile` __

Use this parameter to choose a configuration profile. Profiles can give configuration presets for different compute environments.

Several generic profiles are bundled with the pipeline which instruct the pipeline to use software packaged using different methods (Docker, Singularity, Podman, Shifter, Charliecloud, Apptainer, Conda) - see below.

Important

We highly recommend the use of Docker or Singularity containers for full pipeline reproducibility, however when this is not possible, Conda is also supported. 

The pipeline also dynamically loads configurations from <https://github.com/nf-core/configs> when it runs, making multiple config profiles for various institutional clusters available at run time. For more information and to check if your system is supported, please see the [nf-core/configs documentation](https://github.com/nf-core/configs#documentation).

Note that multiple profiles can be loaded, for example: `-profile test,docker` \- the order of arguments is important! They are loaded in sequence, so later profiles can overwrite earlier profiles.

If `-profile` is not specified, the pipeline will run locally and expect all software to be installed and available on the `PATH`. This is _not_ recommended, since it can lead to different results on different machines dependent on the computer environment.

  * `test`
    * A profile with a complete configuration for automated testing
    * Includes links to test data so needs no other parameters
  * `docker`
    * A generic configuration profile to be used with [Docker](https://docker.com/)
  * `singularity`
    * A generic configuration profile to be used with [Singularity](https://sylabs.io/docs/)
  * `podman`
    * A generic configuration profile to be used with [Podman](https://podman.io/)
  * `shifter`
    * A generic configuration profile to be used with [Shifter](https://nersc.gitlab.io/development/shifter/how-to-use/)
  * `charliecloud`
    * A generic configuration profile to be used with [Charliecloud](https://charliecloud.io/)
  * `apptainer`
    * A generic configuration profile to be used with [Apptainer](https://apptainer.org/)
  * `wave`
    * A generic configuration profile to enable [Wave](https://seqera.io/wave/) containers. Use together with one of the above (requires Nextflow ` 24.03.0-edge` or later).
  * `conda`
    * A generic configuration profile to be used with [Conda](https://conda.io/docs/). Please only use Conda as a last resort i.e. when it’s not possible to run the pipeline with Docker, Singularity, Podman, Shifter, Charliecloud, or Apptainer.
  * `gpu`
    * A generic configuration profile for enabling GPU execution for modules that have `process_gpu` label.

#### `-resume` __

Specify this when restarting a pipeline. Nextflow will use cached results from any pipeline steps where the inputs are the same, continuing from where it got to previously. For input to be considered the same, not only the names must be identical but the files’ contents as well. For more info about this parameter, see [this blog post](https://www.nextflow.io/blog/2019/demystifying-nextflow-resume.html).

You can also supply a run name to resume a specific run: `-resume [run-name]`. Use the `nextflow log` command to show previous run names.

#### `-c` __

Specify the path to a specific config file (this is a core Nextflow command). See the [nf-core website documentation](https://nf-co.re/usage/configuration) for more information.

### Custom configuration __

#### Resource requests __

Whilst the default requirements set within the pipeline will hopefully work for most people and with most input data, you may find that you want to customise the compute resources that the pipeline requests. Each step in the pipeline has a default set of requirements for number of CPUs, memory and time. For most of the pipeline steps, if the job exits with any of the error codes specified [here](https://github.com/nf-core/rnaseq/blob/4c27ef5610c87db00c3c5a3eed10b1d161abf575/conf/base.config#L18) it will automatically be resubmitted with higher resources request (2 x original, then 3 x original). If it still fails after the third attempt then the pipeline execution is stopped.

To change the resource requests, please see the [max resources](https://nf-co.re/docs/usage/configuration#max-resources) and [tuning workflow resources](https://nf-co.re/docs/usage/configuration#tuning-workflow-resources) section of the nf-core website.

#### Custom Containers __

In some cases, you may wish to change the container or conda environment used by a pipeline steps for a particular tool. By default, nf-core pipelines use containers and software from the [biocontainers](https://biocontainers.pro/) or [bioconda](https://bioconda.github.io/) projects. However, in some cases the pipeline specified version maybe out of date.

To use a different container from the default container or conda environment specified in a pipeline, please see the [updating tool versions](https://nf-co.re/docs/usage/configuration#updating-tool-versions) section of the nf-core website.

#### Custom Tool Arguments __

A pipeline might not always support every possible argument or option of a particular tool used in pipeline. Fortunately, nf-core pipelines provide some freedom to users to insert additional parameters that the pipeline does not include by default.

To learn how to provide additional arguments to a particular tool of the pipeline, please see the [customising tool arguments](https://nf-co.re/docs/usage/configuration#customising-tool-arguments) section of the nf-core website.

#### nf-core/configs __

In most cases, you will only need to create a custom config as a one-off but if you and others within your organisation are likely to be running nf-core pipelines regularly and need to use the same settings regularly it may be a good idea to request that your custom config file is uploaded to the `nf-core/configs` git repository. Before you do this please can you test that the config file works with your pipeline of choice using the `-c` parameter. You can then create a pull request to the `nf-core/configs` repository with the addition of your config file, associated documentation file (see examples in [`nf-core/configs/docs`](https://github.com/nf-core/configs/tree/master/docs)), and amending [`nfcore_custom.config`](https://github.com/nf-core/configs/blob/master/nfcore_custom.config) to include your custom profile.

See the main [Nextflow documentation](https://www.nextflow.io/docs/latest/config.html) for more information about creating your own configuration files.

If you have any questions or issues please send us a message on [Slack](https://nf-co.re/join/slack) on the [`#configs` channel](https://nfcore.slack.com/channels/configs).

### Running in the background __

Nextflow handles job submissions and supervises the running jobs. The Nextflow process must run until the pipeline is finished.

The Nextflow `-bg` flag launches Nextflow in the background, detached from your terminal so that the workflow does not stop if you log out of your session. The logs are saved to a file.

Alternatively, you can use `screen` / `tmux` or similar tool to create a detached session which you can log back into at a later time. Some HPC setups also allow you to run nextflow within a cluster job submitted your job scheduler (from where it submits more jobs).

### Nextflow memory requirements __

In some cases, the Nextflow Java virtual machines can start to request a large amount of memory. We recommend adding the following line to your environment to limit this (typically in `~/.bashrc` or `~./bash_profile`):
    
    
    NXF_OPTS='-Xms1g -Xmx4g'

**On this page**

# 工具文档: methylong: Introduction

##  nf-core/methylong

[ __Edit](https://github.com/nf-core/methylong/blob/2.0.0/README.md "Edit this page on GitHub")

Extract methylation calls from long reads (ONT/ PacBio)

dna-methylationfiber-seqlong-readontpacbio

[ __Launch version 2.0.0](/launch/?pipeline=methylong&release=2.0.0) [ __https://github.com/nf-core/methylong](https://github.com/nf-core/methylong/tree/2.0.0)

  * [ __Introduction](/methylong/2.0.0/ "introduction")
  * [ __Usage](/methylong/2.0.0/docs/usage/ "usage")
  * [ __Parameters](/methylong/2.0.0/parameters/ "parameters")
  * [ __Output](/methylong/2.0.0/docs/output/ "output")
  * [ __Results](/methylong/2.0.0/results/methylong/results-3513e80df682ad20f42d6429a2ee142b606949b5/ "results")
  * [ __Releases](/methylong/releases_stats/ "releases")
  * __

2.0.0 
    * [ 2.0.0 ](/methylong/2.0.0)
    * [ 1.0.0 ](/methylong/1.0.0)
    * [ dev ](/methylong/dev)

__Introduction

[ __Introduction](/methylong/2.0.0/)[ __Usage](/methylong/2.0.0/docs/usage/)[ __Parameters](/methylong/2.0.0/parameters/)[ __Output](/methylong/2.0.0/docs/output/)[ __Results](/methylong/2.0.0/results/methylong/results-3513e80df682ad20f42d6429a2ee142b606949b5/)[ __Releases](/methylong/releases_stats/)

__

2.0.0 

  * [ 2.0.0 ](/methylong/2.0.0)
  * [ 1.0.0 ](/methylong/1.0.0)
  * [ dev ](/methylong/dev)

### Introduction __

**nf-core/methylong** is a bioinformatics pipeline that is tailored for long-read methylation calling. This pipeline requires a genome reference as input, and can take either modification-basecalled ONT reads, PacBio HiFi reads (modBam), raw sequencing Pod5 reads or raw Bam reads. The ONT workflow includes modcalling (optional), preprocessing (trim and repair) of reads, genome alignment and methylation calling. The PacBio HiFi workflow includes modcalling (optional), genome alignment and methylation calling. Methylation calls are extracted into BED/BEDGRAPH format, readily for direct downstream analysis. The downstream workflow includes SNV calling, phasing and DMR analysis.

#### ONT workflow:__

  1. modcalling (optional) 
     * basecall pod5 reads to modBam - `dorado basecaller sup --modified-bases 5mC_5hmC` (default)
  2. trim and repair tags of input modBam 
     * trim and repair workflow: 
       1. sort modBam - `samtools sort`
       2. convert modBam to fastq - `samtools fastq`
       3. trim barcode and adapters - `porechop`
       4. convert trimmed modfastq to modBam - `samtools import`
       5. repair MM/ML tags of trimmed modBam - `modkit repair`
  3. align to reference (plus sorting and indexing) - `dorado aligner`( default) / `minimap2`
     * optional: remove previous alignment information before running `dorado aligner` using `samtools reset`
     * include alignment summary - `samtools flagstat`
  4. create bedMethyl - `modkit pileup`, 5x base coverage minimum.
  5. create bedgraphs (optional)

#### PacBio workflow:__

  1. modcalling (optional)

     * modcall bam reads to modBam - `jasmine` (default) or `ccsmeth`
  2. align to reference - `pbmm2` (default) or `minimap2`

     * minimap workflow:

       1. convert modBam to fastq - `samtools convert`
       2. alignment - `minimap2`
       3. sort and index - `samtools sort`
       4. alignment summary - `samtools flagstat`
     * pbmm2 workflow:

       1. alignment and sorting - `pbmm2`
       2. index - `samtools index`
       3. alignment summary - `samtools flagstat`
  3. create bedMethyl - `pb-CpG-tools` (default) or `modkit pileup`

     * notes about using `pb-CpG-tools` pileup: 
       * 5x base coverage minimum.
       * 2 pile up methods available from `pb-CpG-tools`: 
         1. default using `model`
         2. or `count` (differences described here: <https://github.com/PacificBiosciences/pb-CpG-tools>)
       * `pb-CpG-tools` by default merge mC signals on CpG into forward strand. To ‘force’ strand specific signal output, I followed the suggestion mentioned in this issue ([PacificBiosciences/pb-CpG-tools#37](https://github.com/PacificBiosciences/pb-CpG-tools/issues/37)) which uses HP tags to tag forward and reverse reads, so they were output separately.
  4. create bedgraph (optional)

#### Downstream workflow:__

  1. SNV calling - `clair3`
  2. phasing - `whatshap phase`
  3. DMR analysis 
     * includes DMR haplotype level and population scale: 
       1. tag reads by haplotype - `whatshap haplotype`
       2. create bedMethyl - `modkit pileup`
       3. DMR - `DSS` (default) or `modkit dmr`
          * in `DSS` , regions with statistically significant CpG sites will be detected as DMRs.

#### Fiberseq workflow:__

  * ONT alignedBAM 
    1. filtering m6A calls - `modkit call-mods`
    2. infer nucleosomes and MSPs - `ft add-nuleosomes`
    3. create bedMethyl - `ft extract`
  * PacBio alignedBAM 
    1. predict m6a and infer nucleosomes - `ft predict-m6a`
    2. create bedMethyl - `ft extract`

### Usage __

Note

Currently no support of `dorado` and `pb-CpG-tools` through conda.

Note

The pipeline can identify whether ONT reads are in pod5 or bam format, and automatically determine whether to perform `basecalling`.

Note

If you are new to Nextflow and nf-core, please refer to [this page](https://nf-co.re/docs/usage/installation) on how to set-up Nextflow. Make sure to [test your setup](https://nf-co.re/docs/usage/introduction#how-to-run-a-pipeline) with `-profile test` before running the workflow on actual data.

#### Required input:__

  * ONT or PacBio HiFi reads 
    * unaligned modification basecalled bam (modBam)
    * if input modBam was aligned, remove previous alignment information using `--reset`
    * raw ONT pod5
    * raw bam
  * reference genome

First, prepare a samplesheet with your input data that looks as follows:

samplesheet.csv
    
    
    group,sample,path,ref,method
    test,Col_0,ont_modbam.bam,Col_0.fasta,ont
     

Column| Content  
---|---  
`group`| Group of the sample  
`sample`| Name of the sample  
`path`| Path to sample file  
`ref`| Path to assembly fasta/fa file  
`method`| specify ont / pacbio  
  
Now, you can run the pipeline using:
    
    
    nextflow run nf-core/methylong \
       -profile <docker/singularity/.../institute> \
       --input samplesheet.csv \
       --outdir <OUTDIR>

Warning

Please provide pipeline parameters via the CLI or Nextflow `-params-file` option. Custom config files including those provided by the `-c` Nextflow option can be used to provide any configuration _**except for parameters**_ ; see [docs](https://nf-co.re/docs/usage/getting_started/configuration#custom-configuration-files).

For more details and further functionality, please refer to the [usage documentation](https://nf-co.re/methylong/usage) and the [parameter documentation](https://nf-co.re/methylong/parameters).

### Pipeline output __

To see the results of an example test run with a full size dataset refer to the [results](https://nf-co.re/methylong/results) tab on the nf-core website pipeline page. For more details about the output files and reports, please refer to the [output documentation](https://nf-co.re/methylong/output).

Folder stuctures of the outputs:
    
    
     
    ├── ont/sampleName
    │   │
    │   ├── fastqc
    │   │
    │   ├── basecall
    │   │   └── calls.bam
    │   │
    │   ├── fiberseq
    │   │   ├── m6acall.bam
    │   │   └── m6a.bed
    │   │
    │   ├── trim
    │   │   ├── trimmed.fastq.gz
    │   │   └── trimmed.log
    │   │
    │   ├── repair
    │   │   ├── repaired.bam
    │   │   └── repaired.log
    │   │
    │   ├── alignment
    │   │   ├── aligned.bam
    │   │   ├── aligned.bai
    │   │   └── aligned.flagstat
    │   │
    │   ├── snvcall
    │   │   ├── merge_output.vcf.gz
    │   │   ├── merge_output.vcf.gz.tbi
    │   │   └── SNV_PASS.vcf
    │   │
    │   ├── phase
    │   │   ├── phased.vcf
    │   │   ├── haplotagged.bam
    │   │   └── haplotagged.readlist
    │   │
    │   ├── pileup/modkit
    │   │   ├── pileup.bed.gz
    │   │   └── pileup.log
    │   │
    │   ├── bedgraph
    │   │   └── bedgraphs
    │   │
    │   ├── dmr_haplotype_level/dss
    │   │   ├── preprocessed_<1|2|etc>.bed
    │   │   ├── DSS_DMLtest.txt
    │   │   ├── DSS_callDML.txt
    │   │   ├── DSS_callDMR.txt
    │   │   └── DSS.log
    │   │
    │   └── dmr_population_scale
    │       ├── population_scale_DMLtest.txt
    │       ├── population_scale_callDML.txt
    │       ├── population_scale_callDMR.txt
    │       └── population_scale.log
    │
    │
    ├── pacbio/sampleName
    │   │
    │   ├── fastqc
    │   │
    │   ├── modcall
    │   │   └── modbam.bam
    │   │
    │   ├── fiberseq
    │   │   ├── m6a_predicted.bam
    │   │   └── m6a.bed
    │   │
    │   ├── aligned_minimap2/ aligned_pbmm2
    │   │   ├── aligned.bam
    │   │   ├── aligned.bai/csi
    │   │   └── aligned.flagstat
    │   │
    │   ├── pileup: modkit/pb_cpg_tools
    │   │   ├── pileup.bed.gz
    │   │   ├── pileup.log
    │   │   └── pileup.bw (only pb_cpg_tools)
    │   │
    │   ├── snvcall
    │   │   ├── merge_output.vcf.gz
    │   │   └── SNV_PASS.vcf
    │   │
    │   ├── phase
    │   │   ├── phased.vcf
    │   │   ├── haplotagged.bam
    │   │   └── haplotagged.readlist
    │   │
    │   ├── bedgraph
    │   │   └── bedgraphs
    │   │
    │   ├── dmr_haplotype_level/dss
    │   │   ├── preprocessed_1.bed
    │   │   ├── preprocessed_2.bed
    │   │   ├── DSS_DMLtest.txt
    │   │   ├── DSS_callDML.txt
    │   │   ├── DSS_callDMR.txt
    │   │   └── DSS.log
    │   │
    │   └── dmr_population_scale
    │       ├── population_scale_DMLtest.txt
    │       ├── population_scale_callDML.txt
    │       ├── population_scale_callDMR.txt
    │       └── population_scale.log
    │
    │
    └── multiqc
        │
        ├── fastqc
        └── flagstat
     

bedgraph outputs all have min. 5x base coverage.

### Credits __

nf-core/methylong was originally written by [Jin Yan Khoo](https://github.com/jkh00), from the Faculty of Biology of the Ludwig-Maximilians University (LMU) in Munich, Germany. Further significant contributions were made by [YiJin Xiong](https://github.com/YiJin-Xiong), from Central South University (CSU) in Changsha, China.

I thank the following people for their extensive assistance in the development of this pipeline:

  * [Felix Lenner](https://github.com/fellen31)
  * [Júlia Mir Pedrol](https://github.com/mirpedrol)
  * [Matthias Hörtenhuber](https://github.com/mashehu)
  * [Sateesh Peri](https://github.com/sateeshperi)
  * [Niklas Schandry](https://github.com/nschan)

### Contributions and Support __

If you would like to contribute to this pipeline, please see the [contributing guidelines](https://github.com/nf-core/methylong/blob/2.0.0/.github/CONTRIBUTING.md).

For further information or help, don’t hesitate to get in touch on the [Slack `#methylong` channel](https://nfcore.slack.com/channels/methylong) (you can join with [this invite](https://nf-co.re/join/slack)).

### Citations __

If you use nf-core/methylong for your analysis, please cite it using the following doi: [10.5281/zenodo.15366448](https://doi.org/10.5281/zenodo.15366448)

An extensive list of references for the tools used by the pipeline can be found in the [`CITATIONS.md`](https://github.com/nf-core/methylong/blob/2.0.0/CITATIONS.md) file.

You can cite the `nf-core` publication as follows:

> **The nf-core framework for community-curated bioinformatics pipelines.**
> 
> Philip Ewels, Alexander Peltzer, Sven Fillinger, Harshil Patel, Johannes Alneberg, Andreas Wilm, Maxime Ulysse Garcia, Paolo Di Tommaso & Sven Nahnsen.
> 
> _Nat Biotechnol._ 2020 Feb 13. doi: [10.1038/s41587-020-0439-x](https://dx.doi.org/10.1038/s41587-020-0439-x).

#######  __run with

__

__

__

See the [docs](https://github.com/seqeralabs/tower-cli/#2-configuration) on how to configure the Seqera Platform CLI.

  * nf-core
  * Nextflow
  * Seqera Platform

#######  subscribers

181

#######  stars

22

#######  open issues

3

#######  open PRs

1

#######  last release

4 months ago

#######  last update

4 months ago

#######  included modules 

[clair3](/modules/clair3/)[fastqc](/modules/fastqc/)[fibertoolsrs_addnucleosomes](/modules/fibertoolsrs_addnucleosomes/)[fibertoolsrs_extract](/modules/fibertoolsrs_extract/)[fibertoolsrs_predictm6a](/modules/fibertoolsrs_predictm6a/) and 18 more modules

#######  included subworkflows 

[utils_nextflow_pipeline](/subworkflows/utils_nextflow_pipeline/)[utils_nfcore_pipeline](/subworkflows/utils_nfcore_pipeline/)[utils_nfschema_plugin](/subworkflows/utils_nfschema_plugin/)

#######  contributors 

[ ](https://github.com/YiJin-Xiong)

[ ](https://github.com/jkh00)

[ ](https://github.com/jfy133)

#######  get help 

[__Ask a question on Slack](https://nfcore.slack.com/channels/methylong) [__Open an issue on GitHub](https://github.com/nf-core/methylong/issues)

# 工具文档: methylong: Parameters

##  nf-core/methylong

Extract methylation calls from long reads (ONT/ PacBio)

dna-methylationfiber-seqlong-readontpacbio

[ __Launch version 2.0.0](/launch/?pipeline=methylong&release=2.0.0) [ __https://github.com/nf-core/methylong](https://github.com/nf-core/methylong/tree/2.0.0)

  * [ __Introduction](/methylong/2.0.0/ "introduction")
  * [ __Usage](/methylong/2.0.0/docs/usage/ "usage")
  * [ __Parameters](/methylong/2.0.0/parameters/ "parameters")
  * [ __Output](/methylong/2.0.0/docs/output/ "output")
  * [ __Results](/methylong/2.0.0/results/methylong/results-3513e80df682ad20f42d6429a2ee142b606949b5/ "results")
  * [ __Releases](/methylong/releases_stats/ "releases")
  * __

2.0.0 
    * [ 2.0.0 ](/methylong/2.0.0/parameters)
    * [ 1.0.0 ](/methylong/1.0.0/parameters)
    * [ dev ](/methylong/dev/parameters)

__Parameters

[ __Introduction](/methylong/2.0.0/)[ __Usage](/methylong/2.0.0/docs/usage/)[ __Parameters](/methylong/2.0.0/parameters/)[ __Output](/methylong/2.0.0/docs/output/)[ __Results](/methylong/2.0.0/results/methylong/results-3513e80df682ad20f42d6429a2ee142b606949b5/)[ __Releases](/methylong/releases_stats/)

__

2.0.0 

  * [ 2.0.0 ](/methylong/2.0.0/parameters)
  * [ 1.0.0 ](/methylong/1.0.0/parameters)
  * [ dev ](/methylong/dev/parameters)

### ____Input/output options

Define where the pipeline should find input data and save output data.

____`--input`

Path to comma-separated file containing information about the samples in the experiment.

required

type: `string`

Help text

____`--outdir`

The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure.

required

type: `string`

____`--email`

Email address for completion summary.

type: `string`

pattern: `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$`

Help text

____`--multiqc_title`

MultiQC report title. Printed as page header, used for filename if not otherwise specified.

type: `string`

### ____Institutional config options

Parameters used to describe centralised config profiles. These should not be edited.

____`--custom_config_version`

Git commit id for Institutional configs.

hidden

type: `string`

default: `master`

____`--custom_config_base`

Base directory for Institutional configs.

hidden

type: `string`

default: `https://raw.githubusercontent.com/nf-core/configs/master`

Help text

____`--config_profile_name`

Institutional config name.

hidden

type: `string`

____`--config_profile_description`

Institutional config description.

hidden

type: `string`

____`--config_profile_contact`

Institutional config contact information.

hidden

type: `string`

____`--config_profile_url`

Institutional config URL link.

hidden

type: `string`

### ____Generic options

Less common options for the pipeline, typically set in a config file.

____`--version`

Display version and exit.

hidden

type: `boolean`

____`--publish_dir_mode`

Method used to save pipeline results to output directory.

hidden

type: `string`

symlinkrellinklinkcopy (default)copyNoFollowmove

Help text

____`--email_on_fail`

Email address for completion summary, only when pipeline fails.

hidden

type: `string`

pattern: `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$`

Help text

____`--plaintext_email`

Send plain-text email instead of HTML.

hidden

type: `boolean`

____`--monochrome_logs`

Do not use coloured log outputs.

hidden

type: `boolean`

____`--hook_url`

Incoming hook URL for messaging service

hidden

type: `string`

Help text

____`--validate_params`

Boolean whether to validate parameters against the schema at runtime

hidden

type: `boolean`

default: `true`

____`--pipelines_testdata_base_path`

Base URL or local path to location of pipeline test dataset files

hidden

type: `string`

default: `https://raw.githubusercontent.com/nf-core/test-datasets/`

### ____Mod calling options

__ `--dorado_model`

Specify dorado model, default is sup, other available models can be found on Dorado’s GitHub repository.

type: `string`

default: `sup`

__ `--dorado_modification`

Specify dorado modification, default is 5mC_5hmC, other available modifications can be found on Dorado’s GitHub repository.

type: `string`

default: `5mC_5hmC`

__ `--pacbio_modcall`

Indicate if required modcalling in PacBio workflow

type: `boolean`

__ `--pacbio_modcaller`

Modcaller option in PacBio workflow, default is jasmine, specify ccsmeth to switch

type: `string`

jasmine (default)ccsmeth

__ `--ccsmeth_cm_model`

Ccsmeth call mods model.

type: `string`

default: `${projectDir}/bin/ccsmeth_models/model_ccsmeth_5mCpG_call_mods_attbigru2s_b21.v3.ckpt`

__ `--ccsmeth_ag_model`

Ccsmeth call freqb model.

type: `string`

default: `${projectDir}/bin/ccsmeth_models/model_ccsmeth_5mCpG_aggregate_attbigru_b11.v2p.ckpt`

### ____Preprocessing options

__ `--reset`

Removes the alignment information added by aligners and updates flags accordingly

type: `boolean`

__ `--no_trim`

Skip trimming in ONT workflow, will directly start from alignment step

type: `boolean`

### ____Alignment options

__ `--ont_aligner`

Aligner option in ONT workflow, default is dorado aligner, specify minimap2 to switch

type: `string`

dorado (default)minimap2

__ `--pacbio_aligner`

Aligner option in PacBio workflow, default is pbmm2, specify minimap2 to switch

type: `string`

pbmm2 (default)minimap2

### ____Mod pileup options

__ `--pileup_method`

Pileup method in PacBio workflow, default is pbcpgtools, specify modkit to switch

type: `string`

pbcpgtools (default)modkit

__ `--pileup_count`

Specify pbcpgtools pileup mode, default is using model mode, specify this parameter to switch to count mode

type: `boolean`

default: `model`

__ `--denovo`

This option will identify and output all CG sites found in the consensus sequence from the reads in the `pb-CpG-tools`pileup (reference free); by default reference sequences are used to identify and output all CG sites.

type: `boolean`

__ `--bedgraph`

Indicate if required bedgraphs as output

type: `boolean`

__ `--all_contexts`

Specify pileup context

type: `boolean`

__ `--m6a`

Indicate if pileup m6a motif

type: `boolean`

### ____Fiberseq options

__ `--fiberseq`

Indicate if required m6a calling for fiberseq data

type: `boolean`

### ____DMR options

__ `--skip_snvs`

Indicate if to skip snvcall and phase

type: `boolean`

__ `--haplotype_dmrer`

DMRer option in DMR analysis for haplotype level, default is dss, specify modkit to switch

type: `string`

dss (default)modkit

__ `--dmr_population_scale`

Indicate if required DMR analysis for population scale

type: `boolean`

__ `--population_dmrer`

DMRer option in DMR analysis for population scale, default is dss, specify modkit to switch

type: `string`

dss (default)modkit

__ `--dmr_a`

One of the group of DMR analysis in population scale

type: `string`

__ `--dmr_b`

Another group of DMR analysis in population scale

type: `string`

### ____Multiqc

____`--multiqc_config`

Custom config file to supply to MultiQC.

hidden

type: `string`

____`--multiqc_logo`

Custom logo file to supply to MultiQC. File name must also be set in the MultiQC config file

hidden

type: `string`

____`--multiqc_methods_description`

Custom MultiQC yaml file containing HTML including a methods description.

type: `string`

____`--max_multiqc_email_size`

File size limit when attaching MultiQC reports to summary emails.

hidden

type: `string`

default: `25.MB`

pattern: `^\d+(\.\d+)?\.?\s*(K|M|G|T)?B$`

____`--trace_report_suffix`

Suffix to add to the trace report filename. Default is the date and time in the format yyyy-MM-dd_HH-mm-ss.

hidden

type: `string`

__ `--help`

Display the help message.

type: `boolean,string`

__ `--help_full`

Display the full detailed help message.

type: `boolean`

__ `--show_hidden`

Display hidden parameters in the help message (only works when —help or —help_full are provided).

type: `boolean`

**On this page**

# 工具文档: methylong: Results

##  nf-core/methylong

Extract methylation calls from long reads (ONT/ PacBio)

dna-methylationfiber-seqlong-readontpacbio

[ __Launch version 2.0.0](/launch/?pipeline=methylong&release=2.0.0) [ __https://github.com/nf-core/methylong](https://github.com/nf-core/methylong/tree/2.0.0)

  * [ __Introduction](/methylong/2.0.0/ "introduction")
  * [ __Usage](/methylong/2.0.0/docs/usage/ "usage")
  * [ __Parameters](/methylong/2.0.0/parameters/ "parameters")
  * [ __Output](/methylong/2.0.0/docs/output/ "output")
  * [ __Results](/methylong/2.0.0/results/methylong/results-3513e80df682ad20f42d6429a2ee142b606949b5/ "results")
  * [ __Releases](/methylong/releases_stats/ "releases")
  * __

2.0.0 
    * [ 2.0.0 ](/methylong/2.0.0/results/)
    * [ 1.0.0 ](/methylong/1.0.0/results/)
    * [ dev ](/methylong/dev/results/)

__Results

[ __Introduction](/methylong/2.0.0/)[ __Usage](/methylong/2.0.0/docs/usage/)[ __Parameters](/methylong/2.0.0/parameters/)[ __Output](/methylong/2.0.0/docs/output/)[ __Results](/methylong/2.0.0/results/methylong/results-3513e80df682ad20f42d6429a2ee142b606949b5/)[ __Releases](/methylong/releases_stats/)

__

2.0.0 

  * [ 2.0.0 ](/methylong/2.0.0/results/)
  * [ 1.0.0 ](/methylong/1.0.0/results/)
  * [ dev ](/methylong/dev/results/)

* Name Last Modified Size

[ __pipeline_info/ ](/methylong/2.0.0/results/methylong/results-3513e80df682ad20f42d6429a2ee142b606949b5/pipeline_info/)

# 工具文档: methylong: Results

##  nf-core/methylong

Extract methylation calls from long reads (ONT/ PacBio)

dna-methylationfiber-seqlong-readontpacbio

[ __Launch version 2.0.0](/launch/?pipeline=methylong&release=2.0.0) [ __https://github.com/nf-core/methylong](https://github.com/nf-core/methylong/tree/2.0.0)

  * [ __Introduction](/methylong/2.0.0/ "introduction")
  * [ __Usage](/methylong/2.0.0/docs/usage/ "usage")
  * [ __Parameters](/methylong/2.0.0/parameters/ "parameters")
  * [ __Output](/methylong/2.0.0/docs/output/ "output")
  * [ __Results](/methylong/2.0.0/results/methylong/results-3513e80df682ad20f42d6429a2ee142b606949b5/ "results")
  * [ __Releases](/methylong/releases_stats/ "releases")
  * __

2.0.0 
    * [ 2.0.0 ](/methylong/2.0.0/results/)
    * [ 1.0.0 ](/methylong/1.0.0/results/)
    * [ dev ](/methylong/dev/results/)

__Results

[ __Introduction](/methylong/2.0.0/)[ __Usage](/methylong/2.0.0/docs/usage/)[ __Parameters](/methylong/2.0.0/parameters/)[ __Output](/methylong/2.0.0/docs/output/)[ __Results](/methylong/2.0.0/results/methylong/results-3513e80df682ad20f42d6429a2ee142b606949b5/)[ __Releases](/methylong/releases_stats/)

__

2.0.0 

  * [ 2.0.0 ](/methylong/2.0.0/results/)
  * [ 1.0.0 ](/methylong/1.0.0/results/)
  * [ dev ](/methylong/dev/results/)

* Name Last Modified Size

[ __pipeline_info/ ](/methylong/2.0.0/results/methylong/results-3513e80df682ad20f42d6429a2ee142b606949b5/pipeline_info/)

# 工具文档: methylong: Results

##  nf-core/methylong

Extract methylation calls from long reads (ONT/ PacBio)

dna-methylationfiber-seqlong-readontpacbio

[ __Launch version 2.0.0](/launch/?pipeline=methylong&release=2.0.0) [ __https://github.com/nf-core/methylong](https://github.com/nf-core/methylong/tree/2.0.0)

  * [ __Introduction](/methylong/2.0.0/ "introduction")
  * [ __Usage](/methylong/2.0.0/docs/usage/ "usage")
  * [ __Parameters](/methylong/2.0.0/parameters/ "parameters")
  * [ __Output](/methylong/2.0.0/docs/output/ "output")
  * [ __Results](/methylong/2.0.0/results/methylong/results-3513e80df682ad20f42d6429a2ee142b606949b5/ "results")
  * [ __Releases](/methylong/releases_stats/ "releases")
  * __

2.0.0 
    * [ 2.0.0 ](/methylong/2.0.0/results/)
    * [ 1.0.0 ](/methylong/1.0.0/results/)
    * [ dev ](/methylong/dev/results/)

__Results

[ __Introduction](/methylong/2.0.0/)[ __Usage](/methylong/2.0.0/docs/usage/)[ __Parameters](/methylong/2.0.0/parameters/)[ __Output](/methylong/2.0.0/docs/output/)[ __Results](/methylong/2.0.0/results/methylong/results-3513e80df682ad20f42d6429a2ee142b606949b5/)[ __Releases](/methylong/releases_stats/)

__

2.0.0 

  * [ 2.0.0 ](/methylong/2.0.0/results/)
  * [ 1.0.0 ](/methylong/1.0.0/results/)
  * [ dev ](/methylong/dev/results/)

* Name Last Modified Size

[ __.. ](/methylong/2.0.0/results/methylong/results-3513e80df682ad20f42d6429a2ee142b606949b5/)

[ execution_report_2025-11-21_02-28-05.html](?file=execution_report_2025-11-21_02-28-05.html)

4 months 2.93 MB

[ Download file](https://nf-core-awsmegatests.s3-eu-west-1.amazonaws.com/methylong/results-3513e80df682ad20f42d6429a2ee142b606949b5/pipeline_info/execution_report_2025-11-21_02-28-05.html) Copy file URL Copy S3 URL

[ execution_report_2026-02-16_10-30-25.html](?file=execution_report_2026-02-16_10-30-25.html)

about 1 month 2.93 MB

[ Download file](https://nf-core-awsmegatests.s3-eu-west-1.amazonaws.com/methylong/results-3513e80df682ad20f42d6429a2ee142b606949b5/pipeline_info/execution_report_2026-02-16_10-30-25.html) Copy file URL Copy S3 URL

[ execution_trace_2025-11-21_02-28-05.txt](?file=execution_trace_2025-11-21_02-28-05.txt)

4 months 101 B

[ Download file](https://nf-core-awsmegatests.s3-eu-west-1.amazonaws.com/methylong/results-3513e80df682ad20f42d6429a2ee142b606949b5/pipeline_info/execution_trace_2025-11-21_02-28-05.txt) Copy file URL Copy S3 URL

[ execution_trace_2026-02-16_10-30-25.txt](?file=execution_trace_2026-02-16_10-30-25.txt)

about 1 month 101 B

[ Download file](https://nf-core-awsmegatests.s3-eu-west-1.amazonaws.com/methylong/results-3513e80df682ad20f42d6429a2ee142b606949b5/pipeline_info/execution_trace_2026-02-16_10-30-25.txt) Copy file URL Copy S3 URL

[ nf_core_methylong_software_mqc_versions.yml](?file=nf_core_methylong_software_mqc_versions.yml)

about 1 month 71 B

[ Download file](https://nf-core-awsmegatests.s3-eu-west-1.amazonaws.com/methylong/results-3513e80df682ad20f42d6429a2ee142b606949b5/pipeline_info/nf_core_methylong_software_mqc_versions.yml) Copy file URL Copy S3 URL

[ params_2025-11-21_02-28-43.json](?file=params_2025-11-21_02-28-43.json)

4 months 2.08 kB

[ Download file](https://nf-core-awsmegatests.s3-eu-west-1.amazonaws.com/methylong/results-3513e80df682ad20f42d6429a2ee142b606949b5/pipeline_info/params_2025-11-21_02-28-43.json) Copy file URL Copy S3 URL

[ params_2026-02-16_10-31-04.json](?file=params_2026-02-16_10-31-04.json)

about 1 month 2 kB

[ Download file](https://nf-core-awsmegatests.s3-eu-west-1.amazonaws.com/methylong/results-3513e80df682ad20f42d6429a2ee142b606949b5/pipeline_info/params_2026-02-16_10-31-04.json) Copy file URL Copy S3 URL

[ pipeline_dag_2025-11-21_02-28-05.html](?file=pipeline_dag_2025-11-21_02-28-05.html)

4 months 9.63 kB

[ Download file](https://nf-core-awsmegatests.s3-eu-west-1.amazonaws.com/methylong/results-3513e80df682ad20f42d6429a2ee142b606949b5/pipeline_info/pipeline_dag_2025-11-21_02-28-05.html) Copy file URL Copy S3 URL

[ pipeline_dag_2026-02-16_10-30-25.html](?file=pipeline_dag_2026-02-16_10-30-25.html)

about 1 month 9.63 kB

[ Download file](https://nf-core-awsmegatests.s3-eu-west-1.amazonaws.com/methylong/results-3513e80df682ad20f42d6429a2ee142b606949b5/pipeline_info/pipeline_dag_2026-02-16_10-30-25.html) Copy file URL Copy S3 URL
