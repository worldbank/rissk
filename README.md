
This package creates an **Unit Risk Score (URS)** from **[Survey Solutions](https://mysurvey.solutions/en/)** export files that provides an indication of how much individual interviews are at risk of including undesired interviewer behaviour such as data fabrication. The package extracts a range of features from the microdata and paradata and identifies anomalies. Individual scores are combined into the URS ranging from 0 to 100. The package is generic and can be easily applied to most CAPI or CATI surveys run in Survey Solutions without any modifications. 

# Getting Started

These instructions will guide you on how to install and run this package on your local machine.

## Prerequisites
    
Make sure you have Python 3.8 or higher installed on your machine. You can verify this by running:

```shell
python --version
```
## Setup
1. (Optional) When setting up MLSS, a project folder `mlss` will be created on your local machine. Navigate to the directory where you would like the `mlss` folder to be created. If not done, the directory `mlss` will be created in your currently active working directory. For example, to create the `mlss` directory in `users/USER/projects`: 
```
cd /Users/USER/projects
```
2. Clone this repository to your local machine.
```
git clone git@github.com:RowSquared/mlss.git
```
3. Navigate into the project directory `mlss`.
```
cd mlss
```
4. Create a new virtual environment inside the project directory.
```
python -m venv venv
```
5. Activate the virtual environment. The command to do this will depend on your operating system:
On **Windows**:
```
venv\Scripts\activate
```
On **Unix or MacOS**:
```
source venv/bin/activate
```
6. Install the required dependencies:
```
pip install -r requirements.txt
```
## Running the Package

1. Export from Survey Solutions the Main Survey Data and Paradata for all versions of one questionnaire (survey template). The Main Survey Data must be either in **Tab separated** or **Stata 14** format, and must **Include meta information about questionnaire**.

2. Place the exported zip files into a folder. The path to this folder is referred to below as *<export_path>*. Do not modify the zip files. The folder must contain one zip file for Paradata and one zip file for Main Survey Data for each version of the questionnaire that should be analysed. To exclude versions, do not add their files

3. (If running after the installation), navigate to the `mlss` directory.
```
cd /Users/USER/projects/mlss
```

4. Run the package, using below command and replacing  
    
   - `<export_path>` with the string of the path to the directory containing your Survey Solutions export data.
   - `<survey_name>` with the string of the Questionnaire variable defined in the Survey Solutions Designer, or the beginning of the name of the exported zip files, e.g., ***<survey_name>**_version_Tabular_All.zip*.
   - `<result_path>` with the string of the directory where the output files should be stored. The argument `data.results` is option. If not specified, results will be stored in directory `mlss/result`.


```
python main.py data.externals=<export_path> surveys=<survey_name> data.results=<result_path>
```

5. After executing the command, you should see console logs indicating the progress of the package. Upon successful completion, a message will confirm that the results have been saved to the specified directory. They INCLUDE XYZ.

# Advanced Use

This chapter provides additional information for users who would like to dig deeper and adjust or expand the functioning of the package. 

## Exclude features

By default, all features are included in the construction of the URS. Users can exclude individual features if they are affecting the score in undesired ways. This may be the case, e.g., if a feature has been observed to drive the URS for some interviews, but external validation have revealed those interviews to be of low-risk. 

To turn off a feature and exclude it from the Unit Risk Score, open 
 `environment/main.yaml` and change the `use:` property to `false` for the respective feature prior to rerunning the package. 
For example, below, the feature`answer_changed` has been excluded from the URS.

```yaml
features:
  answer_time_set:
    use: true
  answer_changed:
    use: false
```

# Process description

This chapter describes in broad terms the individual steps of the package. 

1. **Unzip**. The tool looks within <survey_folder_path> for Survey Solutions export files in the Paradata and STATA or Tabular format that match the questionnaire  <survey_name> . For each version, export files are unzipped to a respective subfolder within `mlss/data/raw/<survey_name>`. Within each subfolder, the file `Questionnaire/content.zip` is unzipped.

2. **Build questionnaire data**. For each version, the tool constructs a dataframe `df_questionnaire` using the questionnaire json file `Questionnaire/content/document.json` and the Excel files contained in `Questionnaire/content/Categories`. The dataframe contains one row for every questionnaire item (e.g., questions, variables, sub-sections, etc.) of the Survey Solutions questionnaire, and columns corresponding to (most of) the item properties (e.g.,  question type, variable name, etc.).

3. **Build microdata**. For each version, the tool identifies all export files within the subfolder containing microdata, i.e. all files whose name does not start with 'interview__' or  'assignment__'. For each file:
   - The export file is loaded as a dataframe.
   - (If loaded from STATA), non-response values are adjusted to match the Tabular export format. 
   - Columns relating to questions containing multiple variables in export files are transformed to a single column (multi-select and list questions to lists, GPS questions to string). 
   - System-generated variables are dropped, i.e.,`['interview__key', 'sssys_irnd', 'has__errors', 'interview__status', 'assignment__id']`. 
   - The dataframe is reshaped to long (melt) and all dataframes for one version are appended. The resulting dataframe contains the columns `['interview__id', 'roster_level', 'variable_name', 'value']`. 
   - All rows relating to disabled questions or Survey Solution variables are dropped.
   - Question properties are merged in from `df_questionnaire`.
   - The resulting dataframe df_microdata contains all microdata that could have been set by the interviewer (or preloaded). 
   - [@Gabriele]: <> (Do we drop those withput occurence in para here, do we drop the variables here, and those without answers?)

4. **Build paradata**: For each version, the paradata file is loaded as dataframe. The column `parameters` is split into `param`, `roster_level` and `answer` and question properties are merged in from `df_questionnaire`. For each interview, only events are kept that precede the first occurrence of of any of the following events, `['RejectedBySupervisor', 'OpenedBySupervisor', 'OpenedByHQ', 'RejectedByHQ']`. This limits the paradata, and all paradata based features to interviewing events, i.e. the interviewing that was done before the first interaction by the supervisor or HQ with the interview file. 

[@Gabriele]: <> (This is done later, correct?)
6. Append versions. The questionnaire, microdata and paradata dataframes are appended for all versions. 
7. Build df_interviewing.
8. Build features. Features are built on the item or unit level. For details on all features, their scope and how they were built, refer to [Features & Scores](features_scores.md).
 

# Integrate into survey

> [!WARNING]  
> The MLSS package is aimed to be an additional source of information. It does not make redundant other components of the data quality assurance system, such as  back-checks, audio audits, indicator monitoring, completion and progress checks or high-frequency checks, as these fulfil other important functions.

[!NOTE]  
> Highlights information that users should take into account, even when skimming.

> [!IMPORTANT]  
> Crucial information necessary for users to succeed.
