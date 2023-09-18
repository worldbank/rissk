This document details the construction of all features and scores used in RISSK. In the development branch, each feature has a corresponding Jupyter notebook stored in `rissk/notebook`. For a deeper dive into the individual feature analyses, users familiar with Python can refer to the respective notebook.

> [!NOTE]  
> Use outline button in the top-right corner for swift navigation between features.

# Definitions

The terms below are frequently used in the ensuing descriptions. Here are their precise meanings:

- **Interviewing events** refer to those events in the paradata that are recorded prior to any recorded action by a Supervisor or HQ role, i.e. the first event of type `['RejectedBySupervisor', 'OpenedBySupervisor', 'RejectedByHQ', 'OpenedByHQ']`. These events approximate the initial interview process, prior to any corrections or updates that may occur after the first intervention by Supervisor or HQ roles.

- **Item** refers to a specific question in Survey Solutions for a given roster row. For questions located on the main questionnaire level, the term "item" is synonymous with the question itself. However, for questions that are part of rosters, each roster row for a question is considered an individual item.

- **Unit** denotes a Survey Solutions interview, uniquely identified by its `interview__id`. 

- **Score Type** are groups of scores that are constructed in similar ways. Refer to chapter [Process description](README.md#generating-scores) for a classification. 

# Features and Scores

The features listed below are included by default in the construction of the `unit_risk_score`.

## answer_changed

This feature identifies atypical number of alterations to question responses.

**Feature**

`f__answer_changed` is derived from all active interviewing events of type `AnswerSet` in the paradata. It quantifies the number of times the response to an item has been modified. Changes are computed as follows:

- For single-answer questions, the answer value is compared with prior answer values for the item (if it exists). The event is counted if there's a discrepancy. 
- For questions of type `MultyOptionsQuestion` and `TextListQuestion`, events are counted if the set of answers no longer contains any elements from the previous set of answers. This can occur if an answer option has been unselected or removed, or if the text of a list item has been removed. 
- For multi-answer questions with Yes/No mode, both sets of Yes and No answers are evaluated and events counted if an answer option has been removed or changed from Yes to No or vice versa.

**Score**

Type 1 Score. Anomalies within `f__answer_changed` are detected using [ECOD](https://arxiv.org/pdf/2201.00382.pdf), an efficient, non-parametric algorithm that leverages cumulative distribution functions. The default contamination level is set to 0.1. If required, it can also be [set manually](README.md#adjusting-contamination-level) or be [determined automatically](README.md#automatically-determining-contamination-level) by the system. Anomalies are detected on the item-level by `variable_name`. 

To clarify, anomalies are unusual high (or low) frequencies of changes to an item's answer, relative to the question's norm. For instance, if altering a member's age is typically done 0-2 times, items with 1 or 2 changes wouldn't be flagged as anomalies. However, if the age of a member is adjusted 3 or more times, this item could be earmarked as anomalous.

`s__answer_changed` represents the fraction of items in an interview that were determined to be anomalous based on their `f__answer_changed` values.

## answer_hour_set

This feature captures active interviewing events that occur during unconventional hours of the day.

**Feature**

`f__answer_hour_set` represents the hour of the day extracted from the paradata, adjusted for timezone and rounded to half-hour intervals. It is constructed on the item level for all active interviewing actions performed by the interviewer in the paradata.

**Score**

Type 1 Score. Anomalies in `f__answer_hour_set` are detected using [ECOD](https://arxiv.org/pdf/2201.00382.pdf), an efficient, non-parametric algorithm that leverages cumulative distribution functions. The default contamination level is set to 0.1. If required, it can also be [set manually](README.md#adjusting-contamination-level) or be [determined automatically](README.md#automatically-determining-contamination-level) by the system. Anomalies are detected on the item level across all observations.

`s__answer_time_set` represents the proportion of anomalies within a given interview. Its values range from 0 (indicating the entire interview was conducted during typical hours) to 1 (indicating the entire interview took place during atypical hours). It's worth noting that this score treats every day identically, without differentiating based on the specific date or day of the week.  

## answer_removed

This feature identifies atypical frequencies of answer removals.

**Feature**

`f__answer_removed` is constructed using interviewing events in the paradata. It counts the number of times an event of type `AnswerRemoved` was logged for an item. These events can result from an interviewer actively deleting an answer or from Survey Solutions removing answers due to specific interviewer actions. Modifying the response of a question linked to a roster can trigger multiple such events.

**Score**

Type 1 Score. Anomalies in `f__answer_removed` are detected using [ECOD](https://arxiv.org/pdf/2201.00382.pdf), an efficient, non-parametric algorithm that leverages cumulative distribution functions. The default contamination level is set to 0.1. If required, it can also be [set manually](README.md#adjusting-contamination-level) or be [determined automatically](README.md#automatically-determining-contamination-level) by the system. Anomalies are detected on the item-level by `variable_name`. 

`s__answer_removed` represents the fraction of items in an interview that were determined to be anomalous based on their `f__answer_removed` values.

## answers_selected

This feature identifies unusual high or low number of answer options selected in multi select options. 

**Feature**
`f__answers_selected` is constructed on the item level for all answered questions of type `MultyOptionsQuestion` in the microdata. It contains:

- For YesNo question, the number of YES options selected.
- For other multi-answer questions, the number of answers selected.

**Score**

Type 1 Score. Anomalies within `f__answers_selected` are detected using [ECOD](https://arxiv.org/pdf/2201.00382.pdf), an efficient, non-parametric algorithm that leverages cumulative distribution functions. The default contamination level is set to 0.1. If required, it can also be [set manually](README.md#adjusting-contamination-level) or be [determined automatically](README.md#automatically-determining-contamination-level) by the system. Anomalies are detected on the item-level by `variable_name`. 

`s__answers_selected` represents the fraction of items in an interview that were determined to be anomalous based on their `f__answers_selected` values.

## answer_duration

This feature highlights anomalous durations, either too short or too long, for individual questions.

**Feature**

`f__answer_duration` is constructed at the item level using active interviewing events from the paradata. It represents the total duration, in seconds, for events of type `AnswerSet` and `AnswerRemoved` linked to an item. It is constructed by:

- Keeping only active interviewing events. This removes events generated by Survey Solutions and events that cannot be attributed to an item. 
- For every event, computing the time interval to its preceding event (sorted by column `order`). 
- Assign a value of NaN (Not a Number) to negative time intervals, which are unrealistic durations often resulting from interviewers altering the tablet's time settings.
- Sum all time intervals for `AnswerSet` and `AnswerRemoved` events related to the item. 

It's important to understand that `f__answer_duration` is an approximation of the actual time taken to answer an item. The open navigation design of Survey Solutions makes it challenging to pinpoint when a question is activated or deactivated. This is approximated using the timestamp of the preceding event and the time the answer is set. During these intervals, interviewers might undertake other tasks without logging any active event, like confirming the response to a prior question. Similarly, brief pauses recorded while administering a question (e.g., when accessing a calculator app) aren't allocated to a particular item.

**Score**

Type 1 Score. First, anomalies in `f__answer_duration` are identified using [ECOD](https://arxiv.org/pdf/2201.00382.pdf), an efficient, non-parametric algorithm that leverages cumulative distribution functions. The default contamination level is set to 0.1. If required, it can also be [set manually](README.md#adjusting-contamination-level) or be [determined automatically](README.md#automatically-determining-contamination-level) by the system. Anomalies are detected on the item-level by `variable_name`.

Subsequently, two scores, `s__answer_duration_lower` and `s__answer_duration_upper` are computed. They represent the share of items in an interview with anomalies at the lower or upper bounds respectively. Lower and upper end anomalies are treated separately as they indicate different potential undesired behaviours. Lower end anomalies point at interviewers rushing or fabricating data, upper end at interviewer struggling (or interview/respondent effects). 

## first_decimal

This feature identifies anomalies in the first two decimal digits in numeric questions.

**Feature**

`f__first_decimal` contains the first two decimal digits of the response to all questions of type `NumericQuestion` in the microdata that are not integer questions (`IsInteger == False`).

**Score**

Type 1 Score. Anomalies within `f__first_decimal` are detected using [COF](https://link.springer.com/chapter/10.1007/3-540-47887-6_53), an proximity-based algorithm that is able to handle outliers deviating from low density patterns. The default contamination level is set to 0.1. If required, it can also be [set manually](README.md#adjusting-contamination-level) or be [determined automatically](README.md#automatically-determining-contamination-level) by the system. Anomalies are detected on the item-level by `variable_name`. 

To clarify, anomalies are unusual first two decimal values, relative to the question's norm. For instance, if most answer values to a question contain decimals such as `[0.25, 0.33, 0.5, 0.66, 0.75]`, a different and rare value such as `0.47` would be flagged as anomaly. 

`s__first_decimal` represents the fraction of items in an interview that were determined to be anomalous based on their `f__first_decimal` values.

## first_digit

This feature detects atypical distribution of first digits in numeric questions.

**Feature**

`f__first_digit` extracts the leading digit from the response of all questions classified as `NumericQuestion` in the microdata.

**Score**

Type 3 Score. `s__first_digit` quantifies the fraction of questions for which a specific interviewer exhibits a distinctly different first digit distribution as compared to their counterparts. The score is constructed by:

- Identifying those `variable_name` where answer values span over three orders of magnitude (a necessary condition for Benford's Law to apply).
- For each interviewer and `variable_name`, compute the [Jensen-Shannon (JS) divergence](https://en.wikipedia.org/wiki/Jensen%E2%80%93Shannon_divergence). This measures the deviation of an interviewer's first digit distribution from the collective distribution of the same variable across all other interviewers.
- Tagging a `variable_name` as anomalous for an interviewer if its JS divergence value is less than half of the median JS divergence value for that variable.
  - For each interviewer, calculating the share of anomalous variables.

## gps

This feature identifies anomalies in the recorded locations for GPS-type questions.

**Feature**

Sub-features `gps_latitude`, `gps_longitude` and `gps_accuracy` are constructed for all items of type GpsCoordinateQuestion in the microdata. It's important to note that there might be no or multiple GPS questions within an interview. Additionally, these GPS questions could refer to various places beyond the interview location, such as the location of household plots. 

**Score**

Type 1 Score. Three distinct scores are derived:

`s__gps_proximity_count`: Represents the total number of items located within a radius of 10 meters, plus the accuracies of both points, of any other points recorded within an interview. Note that high accuracy values could skew this score. The score essentially detects anomalies in location density. For instance, in stratified household surveys, numerous points at the same location could be suspicious. Conversely, in institutional surveys (like school or health center surveys), a high count is expected since interviews are usually conducted at the same location.

`s__gps_extreme_outlier` contains the count of extreme outlier locations in an interview. It indicates locations that were recorded outside the survey area. The score is derived by:
- Computing the median longitude and latitude across all locations to establish a midpoint.
- Determining the distance of each point to this midpoint.
- Calculating the 50th and 75th percentile of the distances, and calculating the range p75-p50. 
- Flagging points as anomalous if their distance to the midpoint exceeds 3.5 times the p75-p50 range. 
- Counting these anomalous points within an interview. The score is treated in absolute terms, ensuring that interviews with any extreme outliers are deemed suspicious without being offset by other non-anomalous points within the same interview.

`s__gps_outlier` counts outlier locations within an interview. While some outliers might indicate legitimately remote locations, many arise from interviewers recording the GPS locations while on the move or at their accommodation. The score is derived by:
- Excluding points flagged as extreme outliers. 
- Detecting anomalies using [COF](https://github.com/yzhao062/pyod#thresholding-outlier-scores) for datasets containing fewer than 10k records, and [LOF](https://github.com/yzhao062/pyod#thresholding-outlier-scores) for larger datasets. Both methods are proximity-based, with COF generally performing better, albeit with higher memory demands.
- Counting these anomalous points within an interview. The score is treated in absolute terms, ensuring that interviews with any extreme outliers are deemed suspicious without being offset by other non-anomalous points within the same interview.

## multi_option_question

This feature identifies interviewers' tendency to repeatedly select the same answer options in multi-select questions.

**Feature**

`f__multi_option_question` is constructed on the item level for all questions of type `MultyOptionsQuestion` in the microdata with fixed answer options (question is not linked), 2 or more answer options, and which are not of the Combobox type. The feature indicates the relative position of the chosen answers: a value of 0 means the top answer was selected, and a value of 1 means the bottom-most answer was selected. The feature is scaled in intervals of 1/N, where N is the total number of answer options available.

**Score**

Type 3 Score. `s__multi_option_question` represents the proportion of questions for a given interviewer where there's a noticeable pattern in selecting similar or identical answer options compared to other interviewers. The score is derived by:

- Identifying those `variable_name` for each interviewer with observations exceeding five times the number of available answer options.
- Computing the entropy for these `variable_name` for each interviewer, capturing the diversity in their answers.
- Designating a `variable_name` as anomalous for an interviewer if its entropy is less than half the median entropy value compared to other interviewers.
- Calculating by interviewer the share of anomalous variables over all variables for which entropy was assessed.

## number_answered

This feature quantifies the total number of answers recorded in an interview.

**Feature**

`s__number_answered` represents the count of answers recorded in the microdata that correspond to interviewing events in the paradata. Multi-select questions contribute as a single count. Answers with values [-999999999, '##N/A##'] are excluded since they signify questions that were enabled but remain unanswered. Survey Solution variables and system generated variables are also excluded. 

**Score**

Type 2 Score.  `s__number_answered` is directly equated to `f__number_answered`.

## pause_count

This feature highlights unusual frequencies of pauses during interviews.

**Feature**

`f__pause_count` is the unit-level count of interviewing events of type `Resumed` or `Restarted` in the paradata. These are logged when the interview has been restarted or if the interviewer application has resumed to be active after the tablet screen was turned off or another application was accessed. It's important to note that this feature includes both short system-recorded pauses and longer deliberate pauses when the interview is intentionally interrupted.

**Score**

Type 2 Score. `s__pause_count` is derived by taking the ratio of `f__pause_count` to `f_number_answered`. This quantifies the frequency of pauses in relation to the length of the interview, measure in question answers. 

## pause_duration

This feature identifies unusual duration of pauses during interviews.

**Feature**

`f__pause_duration` represents the total duration of all pauses in an interview. It is derived by summing up the durations between paradata events of type `Resumed` or `Restarted` and their preceding events. It's important to note that this feature includes the duration of both short system-recorded pauses and longer deliberate pauses when the interview is intentionally interrupted.

**Score**

Type 2 Score. `s__pause_duration` is computed as the proportion between `f__pause_duration` and `f__total_elapsed`. It measures the fraction of the total elapsed time that is attributed to pauses.

## sequence_jump

This feature identifies irregular patterns in the question answering sequence.

**Feature**

`f__sequence_jump` quantifies the number of question sequences the interviewer skipped or jumped over when answering an item, relative to the previous item. It is derived as follows:

- For each item, retain only the last interviewing event of type `AnswerSet` from the paradata. If an item was answered multiple times (e.g., re-answered later during the interview), only the last event is considered.
- For each item, calculate the difference `diff` between the answer sequence (sequential number in paradata, sorted by column `order`) and the question sequence (the order of question in the questionnaire). 
- Determine the change in `diff` relative to the previous item. This step helps in identifying whether (groups of) questions were answered sequentially, even if there were previous sequence jumps. 

A `f__sequence_jump` value of 0 implies that a question was answered immediately after the preceding question, according to the questionnaire sequence. Negative values denote a jump back in the questionnaire sequence, while positive values indicate a forward jump. A positive jump can also arise when preceding questions are disabled and therefore unanswerable. It's worth noting that the initial question in roster instances, other than the first row, often has negative jumps, as interviewers "revert" a few questions in the questionnaire sequence to commence with the subsequent roster item. 

**Score**

Type 1 Score. Anomalies within `f__sequence_jump` are detected using [iNNE](https://onlinelibrary.wiley.com/doi/abs/10.1111/coin.12156), a fast, isolation-based algorithm adept at detecting local anomalies. The default contamination level is set to 0.1. If required, it can also be [set manually](README.md#adjusting-contamination-level) or be [determined automatically](README.md#automatically-determining-contamination-level) by the system. Anomalies are detected on the item-level by `variable_name`. 

In essence, anomalies are considered as unusual sequence jumps to an item. These can arise either from legitimate yet atypical enablement patterns in preceding items or from interviewers skipping or backtracking to answer the item.

`s__sequence_jump` represents the fraction of items in an interview that were determined to be anomalous based on their `f__sequence_jump` values.

## single_question

This feature identifies interviewers' tendency to repeatedly select the same answer options in single-select questions.

**Feature**

`f__single_question` is constructed on the item level for all questions of type `SingleQuestion` in the microdata with fixed answer options (question is not linked), 2 or more answer options, and which are not of the Combobox type. The feature indicates the relative position of the chosen answer: a value of 0 means the top answer was selected, and a value of 1 means the bottom-most answer was selected. The feature is scaled in intervals of 1/N, where N is the total number of answer options available.

**Score**

Type 3 Score. `s__single_question` represents the proportion of questions for a given interviewer where there's a noticeable pattern in selecting similar or identical answer options compared to other interviewers. The score is derived by:

- Identifying those `variable_name` for each interviewer with observations exceeding five times the number of available answer options.
- Computing the entropy for these `variable_name` for each interviewer, capturing the diversity in their answers.
- Designating a `variable_name` as anomalous for an interviewer if its entropy is less than half the median entropy value compared to other interviewers.
- Calculating by interviewer the share of anomalous variables over all variables for which entropy was assessed.

## time_changed

This feature identifies the extent to which tablet time has been adjusted backward in an interview, usually done deliberately by interviewers.

**Feature**

`f__time_changed` is calculated at the unit level by examining the time differences between consecutive active interviewing events recorded in the paradata. All negative time differences, excluding those within a 180-second range, are aggregated. This approach deliberately omits minor negative time intervals (up to 3 minutes) which can arise when questions are answered after initiating a GPS question but before its response has been logged. The negative time differences captured in f__time_changed generally indicate intentional adjustments to the tablet's clock by the interviewer. Such adjustments might be made to alter the timestamps shown in timestamp questions or to give the appearance of conducting interviews at different times or dates.

**Score**

Type 2 Score. `s__time_changed` is computed by rounding `f__time_changed` to the nearest 10 minutes interval. This is done to control sensibility of the algorithm used for score aggregation.

## total_duration

This feature quantifies the total interview duration. 

**Feature**

`s__total_duration` is constructed on the unit level and contains an approximation of the total duration of active interviewing events. It is built by:

- Keeping only active interviewing events, i.e of type `['AnswerSet', 'AnswerRemoved', 'CommentSet', 'Resumed', 'Restarted']`. Note, as of now, events of type `Paused` are excluded and not counted towards the total. 
- For every event, computing the time interval to its preceding event (sorted by column `order`). 
- Assigning NaN (Not a Number) to negative time intervals, which are unrealistic durations often resulting from interviewers altering the tablet's time settings.
- Sum all time intervals for an interview that are shorter than 30 minutes. Longer time intervals occasionally occur, but it is save to assume that no active interviewing activities occurred if no event was recorded in the time interval.

It's important to understand that `f__total_duration` is an approximation of the actual duration of all interviewing events. Pauses are excluded. In the future, it could be considered to include short pauses.

**Score**

Type 2 Score. `s__total_duration` is computed by rounding `f__total_duration` to the nearest 10 minutes interval. This is done to control sensibility of the algorithm used for score aggregation.

## total_elapsed

This feature quantifies the total time that has elapsed in an interview.

**Feature**

`f__total_elapsed` is computed at the unit level by calculating the time difference between the first and last interviewing events recorded in the paradata. It measures the total time that has elapsed from the moment an interview was started to the last action taken by an interviewer before any Supervisor or Headquarters role first interacted with the interview. In scenarios where interviews were conducted in a single session without any interruptions, `f__total_elapsed` closely mirrors `f__total_duration`. However, for interviews that experienced pauses and were resumed later, the elapsed time captured by `f__total_elapsed` could be substantially longer than that of `f__total_duration`.

**Score**

Type 2 Score. First, anomalies in `f__total_elapsed` are identified using [ECOD](https://arxiv.org/pdf/2201.00382.pdf), an efficient, non-parametric algorithm that leverages cumulative distribution functions.

Subsequently, two scores are computed: `s__total_elapsed_lower` and `s__elapse_duration_upper`. Both are boolean values representing anomalies detected at the lower or upper boundaries of elapsed time, respectively. By distinguishing between the lower and upper anomalies, we mitigate potential correlations with the `s__total_duration` score.
