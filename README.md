![RISSK Logo](https://github.com/RowSquared/mlss/blob/main/rissk.png?raw=true)

# What is RISSK?

RISSK creates an easy-to-interpret **Unit Risk Score (URS)** directly from your **[Survey Solutions](https://mysurvey.solutions/en/)** export files. The score indicates the how much individual interviews are at risk of including undesired interviewer behaviour such as data fabrication. RISSK is generic and can easily be integrated into the monitoring system of most CAPI or CATI surveys run in Survey Solutions. It works by extracting a range of generic features from the microdata and paradata exports, identifying anomalies and combining individual scores into the URS using Principal Component Analysis. 

# Getting started

These instructions will guide you on how to install and run RISSK on your local machine.

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
   - `<result_path>` with the string of the directory where the output files should be stored. The argument `data.results` is optional. If not specified, results will be stored in directory `mlss/result`.


```
python main.py data.externals=<export_path> surveys=<survey_name> data.results=<result_path>
```

5. After executing the command, you should see console logs indicating the progress of the package. Upon successful completion, a message will confirm that the results have been saved to the specified directory. They INCLUDE XYZ.

# Advanced Use

This chapter provides additional information for users who would like to dig deeper and adjust or expand the functioning of the package. 

## export score and feature files
Scores files can be exported

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

## Set contamination level

The algorithms used in the calculation of some of the scores require a contamination level to be set. By default, RISSK uses the `medfilt` thresholding method to automatically determine the contamination level. This can be overwritten by specifying the `contamination` parameter for the specific score in the `environment/main.yaml`. In below example, a contamination level of 0.1 will be used for the ECOD algorithm in `answer_changed`.

```yaml
  answer_changed:
    use: true
    parameters:
      contamination: 0.1
```
Refer to [FEATURES_SCORES.md](FEATURES_SCORES.md) to learn for which features the `contamination` parameter can be set.

# Interpretation

MLSS produces `FILE` in folder `FOLDER` containing the URS for each interview. 

Variable `unit_risk_score` contains the URS. It ranges from value 0 for interview(s) with the lowest risk to value 100 for interview(s) with the highest risk. The higher the risk score, the more anomalies have been detected for a given interview in the following dimensions:

- hours of the day during which the interview was conducted
- duration of the interview and of individual questions
- locations (if any GPS questions are set) 
- question sequence followed in the interview
- how answers were changed or removed
- duration of pauses in the interview
- the position and share of answers selected
- the variance and entropy of answers
- the distribution of digits of answers
- number of questions answered and unanswered 

Refer to [FEATURS_SCORES.md](FEATURES_SCORES.md) for a detailed description of all features and scores. In our testing, higher number of anomalies have been indicative of problematic interviewer behaviour, such as data fabrication.

RISSK checks for

> [!WARNING]
> The URS is **NOT** proof of interviewer wrongdoing. It may include **false positives** (legitimate interviews with high URS), e.g., if unusual circumstances drive the score of a valid interview. It may also include **false negatives** (problematic interviews with low URS) if algorithms do not detect anomalies in some of the problematic interviews. Further investigation or evidence is needed, see in chapter [Survey integration](#survey-integration).


<!--equal distance between scores ?-->

3. The URS of an interview may not be improved by rejecting an interview and modifying it. Note, that if the URS changed for an interview between different executions of the package, it is due to other interviews becoming available/excluded for the scoring. 

RISSK identifies anomalies in the following types of interviewer behaviour and interview properties. Interviews with higher URS are more unusual in those dimensions, interviews with lower URS are more normal. 

- **Timing**, such as the day and hours of the day during which the interview was conducted, the duration of the interview and of individual questions, etc.
- **Location**, (if any GPS questions are set), are recorded locations spacial outliers and how many other locations are in the extreme vicinity. 
- **Process**, such as the question sequence followed in the interview, how answers were changed or removed, the patterns of pauses in the interview, etc.
- **Answers**, how do the recorded answers compare to answers in other, e.g. the position or share of answers selected, the variance and entropy of answers, the distribution of digits, etc.
- **Interview properties**, such as how many answers were set, how many are unanswered, etc.  



Does not capture all fakes or files with issues. 

Can be used to guide back checks. 

- from individual surveys cannot be compared. 
- For our test data, unit_risk_scare was a positively scewed distribution, as is common in fraud detection. 
- 
- It only takes the active interviewing time into account, which is defined as xxx. Interviews that were looked at or opened by the supervisor early, e.g. in partial sync, will look strange.
- We only consider questions, as they are actively set by interviewers. 
- The score does not consider outstanding error messages. These are easily usable for survey solution users and should be systematically reviewed. 
Precautions, do not say if >0.5 is fake, researcher who wants to get into one guide, if u are user want to use it, 
- When rerunning with more interviews, the scores for previously scored units WILL change. This is due to more information becoming available. For example, a pattern that was initially isolated and suspicious, may have become more common and less suspicious. 
- Please note that scores of individual interview_files can change over time as other interviews are submitted.  
- Do not give feedback like “Your score is low, you did something wrong”
- Repeated lower scores for one interviewer over time signal issues with this individual interviewer. If fraudulent behaviour cannot be proven, maybe observe the interviewer for an interview to see what they did wrong. Compare the score of observed to other unobserved 

# Process description

How does it work. The 

 The package extracts a range of features from the microdata and paradata and identifies anomalies. Individual scores are combined into the URS ranging from 0 to 100. 

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

5. Append versions. The questionnaire, microdata and paradata dataframes are appended for all versions. 
7. Build df_interviewing.
8. Build features. Features are built on the item or unit level. For details on all features, their scope and how they were built, refer to [Features & Scores](FEATURES_SCORES.md). Features are absolute values on the item or unit level. 

9. Individual scores are combined into the `unit_risk_score` using Principal Component Analysis (PCA). To produce an score on  Scores are normalized and windsorized to reduce extreme outliers.

# Survey integration

> [!WARNING]  
> RISSK is aimed to provide additional information. It does not make redundant other components of a data quality assurance system, such as back-checks, audio audits, indicator monitoring, completion & progress tracking or high-frequency checks. These fulfil other important functions.

If your survey uses multiple questionnaires, such as separate household and community questionnaires, the tool must be run separately for each template. 
The tool is aimed to provide an additional source of information for and should not make redundant other components of the data quality assurance system, such as  back-checks, audio audits, indicator monitoring, completion and progress checks or high-frequency checks, as these fulfil other important functions.
The tool should be run frequently to allow timely identification of and solution to issues. For most surveys, somewhere between daily and weekly should be a good frequency. Keep in mind that, depending on your survey, exporting paradata from Survey Solutions and running the tool may take several minutes. 
Integrating it into the data management and monitoring system is desirable, so all information is available together and executing the script and handling the output is automated. As an example, the tool could be executed as part of the scripts that export from Survey Solutions and its output can be picked up as input in your monitoring dashboard.
The tool is designed to provide additional information at the time of the first review of an interview file (see time-dependence of score in chapter Interpretation).    
2 uses: information for review/investigation/backchecks -> look only at interviews that have newly been added since the last batch. One way of achieving this is for every batch of interviews to review the score for those interviews where in file interview__diagnostics, interview__status== “Completed” and rejections__sup==0 and rejections__hq==0, and take actions accordingly. These can include that a back-check interview or audio review is being triggered, or the interviewer being confronted, a 

have not previously been rejected. 
Second use is to look at the score by interviewer (and potentially team) over time, e.g., by week of field work survey. While scores for individual interviews may not be concerning, aggregating them by interviewer and over time, may show trends that could require action, e.g.,  individual interviewers who perform worse than others on average.

Who interviews to check
check the interviews with the highest values, be diverse in what you check, different interviewers, different days
provide feedback, take actions, make sure interviewers know

How to check

What to do if you find discrepancies. 
don't let interviewers get aways with things. Could be stern warning or dismissal. check other cases by the same interviewer (guided by the score) Reinterview affected households. 



# Limitations

- MLSS assumes that the majority of interviews are conducted as desired, which determines normal behaviour. The scores may break down for surveys with extreme levels of problematic interviewer behaviour.

- With low number of interviews (e.g., during the first few days of fieldwork) the scores are less effective and reliable. 

- MLSS is not reliable for interviews that were in a significant part filled in after the first supervisor or HQ related events in the paradata, e.g. if an interview file was originally submitted almost empty and later rejected to be completed by the interviewer. By design, MLSS only considers the part of the interview that happened prior to the first interaction of a Supervisor or HQ role with the interview file.
- 
- If you use [partial synchronization](https://docs.mysurvey.solutions/headquarters/config/admin-settings/) and would like to use MLSS, Supervisor and HQ roles should not open interview files prior to their completion.  

- MLSS has been tested on laptop with XYZ GB of RAM, for paradata up to x M rows, or a survey of XX questions and YY interviews. To process very large datasets may require a server with higher memory. 

- The tool does not (yet) accept microdata exports from Survey Solutions in the SPSS format. Export to STATA or TAB instead. 

- Interviews containing non-contact or non-response cases may distort the URS, as they often follow a different (much shorter) path in the questionnaire. <!-- @Gabriele, we need to test this -->  
- For barcode, picture, audio and geography questions, no microdata based features have been developed. These questions are only considered through their related events in the paradata. 

- The tool has been conceptualized for CAPI or CATI interviews. It has not been tested for surveys run in Survey Solution’s CAWI mode.

# Confirmation of results

## Testing

confirmation on tests (in our tests we observed that x moving up, moved up the score by ... )

## Experiment

To verify the feature generation, anomaly detection and scoring system, we required survey data with reliable interview-level quality labels.  We infused a real CATI survey (name and details cannot be given due to a non-disclosure agreement) with artificial high-at-risk interviews, by asking interviewers to produce fake interviews just after the completion of the real survey. 7 different scenarios were given to induce variation. For some scenarios, interviewers were incentivized to give their best. 11 interviewers created 1 interview file for each of the following scenarios in sequence.  

1. Non-incentivized. Pretend you are interviewing and fill in the questionnaire.
2. Incentivized. Fake as good as you can, try not to get caught.
Same as Scenario 2.
3. Incentivized. Fake as good as you can, try to be realistic in timings.
4. Incentivized. Fake as good as you can, try to set as real answers as possible. 
5. Non-incentivized. Fake without putting effort.
6. Incentivized. Fake as fast as possible. 

The 77 artificial fake interviews were combined with the 241 real interviews from the survey. Real interviews for this survey are believed to be of general low-risk, as they were conducted by a small team of interviewers with a trusted, long-term relationship, incentives to perform well and deterrents to do badly, as well as a good data monitoring structure in place. Furthermore, interviewers were aware that the data they collected would be used to validate secondary data and that discrepancies would be investigated. Nevertheless, it could not be ruled out that some real interviews contained problematic interviewer behaviour. 

# Roadmap

The following additions to the methodology, package and dissemination can be explored in the future.

- **Additional robustness checks**. While features, scores and algorithms have been tested, further experiments could be conducted to experiment how alternative feature design, scoring algorithms and levels and clustering affect the overall score.


- **Additional features**. Identify new potential features e.g.: 

  - Count of QuestionDeclaredInvalid events in paradata once SurveySolution functionality becomes available.
  - Allow additional user input to specify broad survey parameters, e.g., specify cluster variable (to identify spacial and temporal anomalies)  or expected survey duration in days or sample size.


- **Specific features**. Identify specific (but less common) suspicious events and create features of higher-level information, e.g.:  
  - Unusual sequence jumps to TimeStamps questions are more suspicious than for other questions
  - GPS questions recorded at different time than most of the interview.
  - Removing or changing the answers to gating questions (either linked or trigger enablement) may be indicative of interviewers trying to cut the length if an interview, especially at the beginning of a survey.
  - Distinguish between different roster types. E.g. for list rosters, roster_level can be ignored, as often very homogeneous. For other roster types, the roster_level may carry more meaning 


- **Facilitate ease of use**: Wrapper functions can be written to facilitate easier workflows from other packages used to build survey pipelines, such as R or STATA.


- **Obtain testing/training data**. Additional testing data with interview-level quality labels would improve the validity and expose the package to a larger variety of survey settings, e.g. by:
  - Obtaining data from a survey that used a systematic and thorough review/verification systems (e.g. random audio auditing). 
  - Integrating MLSS into a survey quality system to obtain the above.
  - Produce fake data during training or post-survey.

- **Trained models**. With additional training available, one can test alternative approaches of training models to identify at-risk interviews, using as inputs either constructed micro and paradata dataframes, the features or scores.


- **Other CAPI tools**. Expand to allow inputs from other CAPI tools.


- **Server/API**. Tool to receive quality indication/output (what Gabriele mentioned on last call with WB). Platform to get back reduced feedback to learn.

[@Gabriele]: <> (Details please, what was this idea again?)

- **Dissemination**. Work can be done to raise awareness of the package among potential users and to stimulate the use, such as blog posts, presentations, courses, conference papers or supporting deployment among first users.


time series analysis
time accounting
instead of single variate outlier detection, multi variate 
identify different clusters, fabricating interviewers may be different to interviewers who are struggling, need more detailed labels.

> [!IMPORTANT]  
> Crucial information necessary for users to succeed.
