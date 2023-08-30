![RISSK Logo](https://github.com/RowSquared/mlss/blob/main/rissk.png)

# What is RISSK?

RISSK creates an easy-to-interpret **Unit Risk Score (URS)** directly from your **[Survey Solutions](https://mysurvey.solutions/en/)** export files. The score indicates how much individual interviews are at-risk of including undesired interviewer behaviour such as data fabrication and can be used to target suspicious interviews during verification exercises such as back-check interviews. RISSK is generic and can easily be integrated into the monitoring system of most CAPI or CATI surveys run in Survey Solutions. It works by extracting a range of generic features from the microdata and paradata exports, identifying anomalies and combining individual scores into the URS using Principal Component Analysis. 

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
   - `<output_file>` with the string of the file path of the name of the output csv file. Note, it must include the path, not just the name. If not specified, results will be stored in directory `rissk/result/unit_risk_score.csv`.


```
python main.py export_path=<export_path> output_file=<output_file>
```

5. After executing the command, you should see console logs indicating the progress of the package. Upon successful completion, a message will confirm that the results have been saved to the specified directory. They INCLUDE XYZ.

# Advanced Use

This chapter provides additional information for users who would like to dig deeper and adjust or expand the functioning of the package. 

## Export score and feature files
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

MLSS produces `FILE` in folder `<result_path>` containing the URS for each interview. 

Variable `unit_risk_score` contains the URS. It ranges from value 0 for the interview(s) with the lowest risk to value 100 for interview(s) with the highest risk. The higher the risk score, the more likely it is for an interview file to contain problematic interviewer behaviour, such as data fabrication. To identify such behaviour, RISSK searches for anomalies in the following features:

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

The higher the URS, the more unusual an interview is in the above features, and the more an interview should be prioritized for verification and review. To find out which features and score drive the `unit_risk_score`, use the optional export, see chapter [Export score and feature files](#export-score-and-feature-files). Refer to chapter [Process description](#process-description) for description of how the URS is constructed, and to [FEATURS_SCORES.md](FEATURES_SCORES.md) for details on all features and scores.  

<!-- Gabriele, how does this work? -->

> [!WARNING]
> The URS is **not** proof of interviewer misbehaviour. The score includes **false positives** (legitimate interviews with high URS), e.g., if unusual circumstances cause a high score for a valid interview. It also includes **false negatives** (problematic interviews with low URS) if algorithms do not detect anomalies in some of the problematic interviews. To prove interviewer misbehaviour, further evidence or investigation is needed, see  chapter [Survey integration](#survey-integration).

<!--equal distance between scores ?-->

The URS is a _relative_ measure and depends on the patterns in the interviews in the Survey Solutions export files. If RISSK is executed again with new export files, previously obtained `unit_risk_score` will change for the same interview, since patterns in the export filed will have changed. When comparing the URS between interviews, it is important to use scores that were created using the same export files. The relative nature of the URS also implies that `unit_risk_score` cannot be compared directly between surveys. 

By design, RISSK only considers those parts of the interviews that happened prior to the first interaction by a Supervisor or HQ role with an interview file. This is done to exclude post-interview interviewer actions that would otherwise create confounding patterns. If significant parts of an interview were completed after this interaction, these parts will not be considered, and the URS can be off. This also implies that URS of an interview cannot be improved by rejecting an interview and modifying it.  

Please note the RISSK does not (yet) consider outstanding error messages and interviewer comments set. These are easily accessible in the Survey Solution interface and are ideally reviewed systematically. 

<!-- something on the distribution of the scores, maybe test results? 
For our test data, unit_risk_scare was a positively scewed distribution, as is common in fraud detection. ---> 

# Survey integration

Use RISSK to prioritize the most at-risk interviews in your quality assurance processes (in-depth review, back-checks, audio auditing, etc.), so more issues can be detected more easily. Additionally, the URS can be monitored as an indicator to identify trends by interviewer and over time. This chapter lines out how this can be achieved generally. The best way of integrating RISSK into a survey depends on the specific context and resources available. For specific advice, please contact the authors.

> [!WARNING]  
> RISSK is intended to inform and complement other components of a data quality assurance system, such as back-checks, audio audits or indicator monitoring. It does NOT make them redundant.

Ideally, RISSK is run (and the results reviewed and acted upon) on a regular basis throughout fieldwork, so issues can be detected and resolved as early as possible. For most surveys, somewhere between **daily** and **weekly** should be a good frequency. Usually this implies that the output of RISSK needs to be digested and worked through in batches.

If existing, it is desirable to integrate the package into the survey's data management and monitoring system, so all available monitoring information is combined and executing the package and handling the output is automated. An example set-up can be:
- Execute RISSK as part of the scripts that export from Survey Solutions.
- Using the output, identify the interviews to be verified/reviewed and add them to the backlog for supervisors or data monitors.
- Use the output to summarize the URS together with other indicators in the monitoring dashboard.

The URS is designed to inform the **first** review/verification of an interview file, as it only considers what was answered before a Supervisor or HQ role opened or rejected the file (see chapter [Interpretation](#interpretation)). Interviewer actions that happened after the first rejection must be monitored otherwise.  

For any given batch, it is most efficient to prioritize the interviews with the highest URS for review/verification, as these are most likely to be problematic. In our testing survey, of the 10% interviews with the highest URS, 67% were fabricated. Since the URS also contains false negatives (problematic interviews with lower scores), it may also be desirable to review/verify some interviews with lower URS. As an example, one strategy could be to review/verify for every batch 10% of the interviews with the highest URS, and another 5% selected from the rest (e.g., random, highest URS by interviewer, etc..). 

The review/verification of prioritized interviews can include activities such as:

- Ideally, an external verification of the interview by either: 
  - conducting a short back check interview (to establish if interview happened and verify key questions), 
  - auditing the audio recording of the interview (most insightful about interviewer behaviour).
- In-depth review if the interview and the paradata (though often inconclusive).
- Interviewer queries or confrontation, e.g,. _"Our monitoring system has flagged the interview you did yesterday as very suspicious. Is there something you want to tell me about it?"_. (limited)
- Additional interview observations (only effective for unintentional interviewer wrongdoings)

Keep a structured record of the outcome of the review/verification, i.e. if individual interviews were found to contain problematic behaviour, and if so of what nature. You can use this information to finetune the composition of the URS (see chapter [Advanced use](#advanced-use)). The authors would also welcome such outcome, together with the result files to further improve RISSK.

If interviewer misbehaviour could be verified, clear consequences should follow, e.g., stern warning (_"yellow card"_), loss of bonus, retraining, dismissal. It may also be useful to review/verify other interviews by the same interviewer (guided by the URS), and re-interview all affected respondents if necessary. 

It is usually beneficial to let interviewers know that they are being monitored and that an algorithm is used to identify suspicious interviews. This helps them to do well (people do better if they know it matters what they do) and is a deterrent from doing bad (there is real chance of being caught and there are be consequences). 

However, in your feedback to the field teams, do **NOT** reveal details of the algorithm, such as what features are being checked or the scores that are driving the URS of an interview. Interviewers may start to learn what behaviour to avoid or circumvent, reducing RISSK's ability to identify problematic interviews. As an example, if you are providing feedback such as _"We are checking the hour of the day and I see that you have done this interview at night!"_, the interviewer may start to fabricate interviews during the day instead or change the tablet time. Instead, provide generic feedback _"Your interview has been flagged."_, ask the interviewers to provide you with details about the interview _"When did you do it? With who? How many visits did you need? Any specific things to note?"_ and see if the story matches the paradata. 

To use the URS as a monitoring indicator, average `unit_risk_score` by interviewer (and/or team) and over time (week/month), and visualize it e.g. as part of a survey monitoring dashboard. While individual interviews by one interviewer may not score high enough to be reviewed/verified, a repeated high average score over time for one interviewer may signal potential issues and the need to take action. Monitoring the average URS by interviewer and time also helps to check if interviewers have adjusted to feedback or warnings (lower URS post-intervention) or continue to produce problematic interviews (equal or higher URS).

> [!IMPORTANT]
> If your survey uses multiple questionnaires, such as separate household and community questionnaires, RISSK must be executed separately for each template.

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

<!-- Going to do this or should I delete -->

## Experiment

To verify the feature generation, anomaly detection and scoring system, we required survey data with reliable interview-level quality labels. We infused a real CATI survey (name and details cannot be given due to a non-disclosure agreement) with artificial high-at-risk interviews, by asking interviewers to produce fake interviews just after the completion of the real survey. 7 different scenarios were given to induce variation. For some scenarios, interviewers were incentivized to give their best. 11 interviewers created 1 interview file for each of the following scenarios in sequence, or a total of 77 fake interviews.  

1. Non-incentivized. Pretend you are interviewing and fill in the questionnaire.
2. Incentivized. Fake as good as you can, try not to get caught.
Same as Scenario 2.
3. Incentivized. Fake as good as you can, try to be realistic in timings.
4. Incentivized. Fake as good as you can, try to set as real answers as possible. 
5. Non-incentivized. Fake without putting effort.
6. Incentivized. Fake as fast as possible. 

The artificial fake interviews were combined with all 268 real interviews from the survey to form our testing data set, including 345 interviews in total. Real interviews for this survey are believed to be of general low-risk, as they were conducted by a small team of interviewers with a trusted, long-term relationship, incentives to perform well and deterrents to do badly, as well as a good data monitoring structure in place. Furthermore, interviewers were aware that the data they collected would be used to validate secondary data and that discrepancies would be investigated. Nevertheless, it could not be ruled out that some real interviews contained problematic interviewer behaviour. 

When using `unit_risk_score` to cluster interviews into real and fake, we achieve a [recall](https://en.wikipedia.org/wiki/Precision_and_recall)/[sensitivity](https://en.wikipedia.org/wiki/Sensitivity_and_specificity) of 61 %, i.e. of the artificially created fakes, 61 % were correctly classified. To measure the effectiveness in practical survey setting, we sort the interviews by `unit_risk_score` and select the top _N_ percent of interviews, as one would do when using the URS to prioritize interviews for review/verification. We then calculate `share_urs`, the share of fakes among the selected interviews in percent and compare it to `share_rand`, the share of fakes one would obtain if selecting _N_ percent of interviews at random, which is equal to the prevalence of fakes in the data. The table below summarizes the results for the top 5, 10, 15 and 20 percent.  

|    N | share_urs | share_rand | share_urs/share_rand |
|-----:|----------:|-----------:|---------------------:|
|   5% |     66.1% |      22.4% |                  2.8 |
|  10% |         x |      22.4% |                    x |
|  15% |         y |      22.4% |                    y |
|  20% |         z |      22.4% |                    z |

In our experiment, selecting the top 5% of interviews with the highest URS, would contain xyx % of fake interviews, which is 2.8 times higher than selecting interviews it at random. As more interviews are selected, `share_urs` decreases. If selecting 20% of the interviews based on the URS, ZZZ % will be fake, which is still 1.4. higher than selecting at random.

Below chart summarizes how `share_urs` behaves as we increase the number of interviews selected continuously from 1 to 100 of all interviews. The horizontal line at 22.4% equals `share_rand`. 

<!-- add chart -->

Please note that these results only take into account the classification of interviews into real/fake assigned from the experiment groups. While none of the fake interviews can be without issues, some of the real interviews with relatively high `unit_risk_score` may include problematic behaviour, which would increase `share_urs`. 

> [!NOTE]
> The effectiveness is likely to differ between surveys as it depends on the nature of problematic interviews. 

# Process description

How does it work. The 

 The package extracts a range of features from the microdata and paradata and identifies anomalies. Individual scores are combined into the URS ranging from 0 to 100. 

This chapter describes in broad terms the individual steps of the package. 

**Data preparation**

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

4. **Build paradata**: For each version, the paradata file is loaded as dataframe. The column `parameters` is split into `param`, `roster_level` and `answer` and question properties are merged in from `df_questionnaire`. For each interview, only events are kept that precede the first occurrence of of any of the following events, `['RejectedBySupervisor', 'OpenedBySupervisor', 'OpenedByHQ', 'RejectedByHQ']`. This limits the paradata, and all paradata based features to interviewing events, i.e. the interviewing that was done before the first interaction by the supervisor or HQ with the interview file. 

5. **Append versions**. The questionnaire, microdata and paradata dataframes are appended for all versions. 

**Indicator generation**

7. **Reduce to interviewing events**. The paradata and microdata are reduced to data points created during _interviewing events_ which is an approximation of the initial interview process, prior to any corrections or updates that may occur in an interview file after the first intervention by Supervisor or HQ roles. Interviewing events are identified as all events in the paradata for an interview file prior to the first event of the types: `['RejectedBySupervisor', 'OpenedBySupervisor', 'RejectedByHQ', 'OpenedByHQ']`. For each interview, all subsequent events are removed from the pardata dataframe. The reduced paradata is then merged into the microdata and only those datapoints in the microdata are kept that have been produced during interviewing events.

8. **Construct features**. Features are constructed using the reduced paradata or microdata. Features are built either on the unit level, i.e, the interview, or on the item level, i.e., the answer to a Survey Solutions question on a given roster instance/row. Features are absolute values, such as the duration of a question in seconds. [FEATURES_SCORES.md](FEATURES_SCORES.md) provides a description of how each indicator has been constructed.

**Generating scores**

9. Individual features are evaluated and related scores calculated. While there is some variation, this is most commonly done by identifying anomalies within the feature on the item or unit level and then counting the share of anomalies on the unit level. In some cases the scores are built by normalizing features. For a detailed description of all scores, refer to [FEATURES_SCORES.md](FEATURES_SCORES.md).

10. Individual scores are combined using Principal Component Analysis (PCA), a statistical technique to reduce the complexity of data (here the individual scores) while preserving the maximum amount of information. The result of the PCA is then normalized and [windsorized](https://en.wikipedia.org/wiki/Winsorizing) to reduce extreme outliers. The resulting `unit_risk_score` ranges from 0 to 100. 

<!-- what about the alternative methods, why did we decided against it, why PCS-->

<!-- can we weigh features? -->

# Roadmap

The following can be explored in the future to further increase the effectiveness and usability of RISSK.

- **Additional testing**. While features, scores and algorithms have been thoroughly tested using the available experiment and testing data, further experiments could be conducted to explore how alternative feature design, scoring algorithms and clustering affect the overall score in other survey contexts.

- **Expand/refine methodology**. 
  - Identify new potential features e.g.: 

    - Count of QuestionDeclaredInvalid events in paradata once SurveySolution functionality becomes available.
    - Allow additional user input to specify broad survey parameters, e.g., specify cluster variable (to identify spacial and temporal anomalies)  or expected survey duration in days or sample size. 
    - Sequence jumps to TimeStamps questions are more suspicious than for other questions
    - GPS questions recorded at different time than most of the interview.
    - Removing or changing the answers to gating questions (either linked or trigger enablement) may be indicative of interviewers trying to cut the length if an interview, especially at the beginning of a survey.
  - Time series analysis of pauses.
  - Explore multi-variate anomaly detection 
  - Identify different clusters of unwanted interview behaviour, e.g., fabricating interviewers may be different to interviewers who are struggling.
- **Feedback loop**. Develop a standard framework for users to record the results of the review/verification and make it available as input for RISSK, so RISSK can learn from the review/verification during a survey. 

- **Facilitate ease of use**: 
  - Wrapper functions can be written to facilitate easier workflows from other packages used to build survey pipelines, such as R or STATA.
  - Additional output file containing the scores and/or indicators
  - Output report or dashboard providing the user with additional information, e.g identification of the most influential scores, a dynamic summary of how URS develops over time, by interviewer/team

- **Obtain testing/training data**. Additional testing data with interview-level quality labels would improve the validity and expose the package to a larger variety of survey settings, e.g. by:
  - Obtaining data from a survey that used a systematic and thorough review/verification systems (e.g. random audio auditing). 
  - Integrating RISSK into a survey quality system.
  - Produce fake data during training or post-survey.

- **Trained models**. With additional training available, one can test alternative approaches of training models to identify at-risk interviews, using as inputs either constructed micro and paradata dataframes, the features or scores.

- **Other CAPI tools**. Expand to allow inputs from other CAPI tools.

- **Server/API**. Platform to receive feedback to learn, e.g. score tables and results of review/verification.

- **Dissemination**. Work can be done to raise awareness of the package among potential users and to stimulate the use, such as blog posts, presentations, courses, conference papers or supporting deployment among first users.



