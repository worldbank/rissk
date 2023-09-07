> [!WARNING]  
> Work in progress - please check back in a few days. 

This document details the construction of all features and scores used in RISSK. Each feature has a corresponding Jupyter notebook stored in `rissk/notebook`. For a deeper dive into the individual feature analyses, users familiar with Python can refer to the respective notebook.

> [!NOTE]  
> Use outline button in the top-right corner for swift navigation between features.

# Included

The features listed below are included by default in the construction of the `unit_risk_score`.

## answer_hour_set

This feature captures active interviewing events that occur during unconventional hours of the day.

**Feature**

`f__answer_hour_set` represents the hour of the day extracted from the paradata, adjusted for timezone and rounded to half-hour intervals. It is constructed on the item level for all active interviewing actions performed by the interviewer in the paradata.

**Score**

Type 1 Score. Anomalies in `f__answer_hour_set` across all events are detected using [ECOD](https://arxiv.org/pdf/2201.00382.pdf), an efficient, non-parametric algorithm that leverages cumulative distribution functions. The contamination level is determined automatically by default, but it can also be [set manually](README.md#Advanced-Use) if required.

`s__answer_time_set` represents the proportion of anomalies within a given interview. Its values range from 0 (indicating the entire interview was conducted during typical hours) to 1 (indicating the entire interview took place during atypical hours). It's worth noting that this score treats every day identically, without differentiating based on the specific date or day of the week.  

## answer_changed

This feature highlights interviews with an atypical number of modifications to question responses.

**Feature**

`f__answer_changed` is derived from all active interviewing events of type `AnswerSet` in the paradata. It enumerates how often the response to an item has been altered. Changes are quantified in the following manner:

- For single-answer questions, the answer value is compared with prior answer values for the item (if it exists). The event is counted if there's a discrepancy. 
- For questions of type `MultyOptionsQuestion` and `TextListQuestion`, events are counted if the set of answers no longer contains any elements from the previous set of answers. This can occur if an answer option has been unselected or removed, or if the text of a list item has been removed. 
- For multi-answer questions with Yes/No mode, both sets of Yes and No answers are evaluated and events counted if an answer option has been removed or changed from Yes to No or vice versa.

**Score**

Type 1 Score. Anomalies within `f__answer_changed` are detected using [ECOD](https://arxiv.org/pdf/2201.00382.pdf), an efficient, non-parametric algorithm that leverages cumulative distribution functions. The contamination level is determined automatically by default, but it can also be [set manually](README.md#Advanced-Use) if required. <!-- is below correct?--> Anomalies are detected on the question level (`variable_name`) to reduce disaggregation. Each question is considered to have an anomaly if an anomaly was detected for the question on any `roster_level`. 

`s__answer_changed` is the share of questions answered <!--answers or question?? --> with anomalies in `f__answer_changed` per interview. The value ranges from 0 (no anomalies) to 1 (hypothetical, only anomalies). An anomaly is an unusual high (or low) frequency of changes to the answer of a question. E.g., if it is commonplace for a member list question to be changed 0-2 times, these changes won't be classified as anomalies. However, the question may be deemed anomalous if it has been changed 5 times. 

## answer_removed

This feature captures atypical frequencies of answer removals.

**Feature**

`f__answer_removed` is constructed using interviewing events in the paradata. It counts the number of times an event of type `AnswerRemoved` was logged for an item. These events can result from an interviewer actively deleting an answer or from Survey Solutions removing answers due to specific interviewer actions. Modifying the response of a question linked to a roster can trigger multiple such events.

**Score**

Type 1 Score. Anomalies in `f__answer_removed` are detected using [ECOD](https://arxiv.org/pdf/2201.00382.pdf), an efficient, non-parametric algorithm that leverages cumulative distribution functions. The contamination level is determined automatically by default, but it can also be [set manually](README.md#Advanced-Use) if required. <!-- Below still the case --> Anomalies are detected on the question level (`variable_name`) to reduce disaggregation. Each question is considered to have an anomaly if an anomaly was detected for the question on any `roster_level`. 

`s__answer_removed` is the share of questions in an interview that show anomalies in `f__answer_removed`. The score's range is from 0 (indicating no anomalies) to 1 (a theoretical scenario denoting only anomalies). An anomaly refers to an unusually high or low frequency of answer removals for a question. 

## answer_position

Captures if answer selected for an interviewer
**Feature**

`f__answer_position` is constructed on the item level for all answered questions of type `SingleQuestion` in the microdata with fixed answer options (question is not linked), more than 2 answer options, and are not of type Combobox. It contains the relative position of the selected answer, ranging from 0 (answer on top was selected) to 1 (answer on bottom selected), in intervals of 1/N answer options available. 

**Score**

<!-- given how the score is done, we should remove some of the filters in feature construction, can even include linked ones -->

Type 3 Score. 
average

entropy calculates how predictibale is a

0 entory distribution is highly predictable, means always selects the same values/ answer positions
1 means not predictable, selects often different values 

done at responsible level. if they select the same position. by variable and by responsible, mark as anomalous all those responsibales who have entropy lower than 50% of the median of all other reposnisbles. binary score for each variable name, 

only over those for which it was possible to calcultae the entropy (only for those responsible and vars with min of 5 records )

1. Calculate the entropy for each variable_name per responsible, i.e., one entropy value for each responsible and variable_name.
2. Entropy is calculated only for those varible_name of each responsible that have at least 10 times the number of possible values of the variable_name
3. Mark as "anomalous" any entropy value that is lower than the 50% of the median entropy value
4. Plot the entropy value for each variable name by responsible and colour in red those values that have very low entropy

number of vars with anomalies, over all variables that 

## answers_selected

Detects if unusual many or few have been selected

**Feature**
`f__answers_selected` is constructed on the item level for all answered questions of type `MultyOptionsQuestion` and `TextListQuestion` in the microdata. It contains:

- For YesNo question, the number of YES options selected.
- For other multi-answer questions, the number of answers selected.
- For list questions, the number of items listed.

Andreas to 
**Score**

share of answers selected, identify lower and upper outliers, using ECOD, 



`answer_share_selected`
<!-- @Gabriele, naming? -->
detect unusual high or low number of item selection

andreas check notebook

## answer_duration

**Feature**

`f__answer_duration` is constructed on the item level using active interviewing events in the paradata. It contains the total duration in seconds of events of type `AnswerSet` and `AnswerRemoved` associated with an item. It is built as follows:

- Only active interviewing events are kept. This removes events generated by Survey Solutions and events that cannot be attributed to an item. 
- For every event, the time interval to the previous event (by column `order`) is calculated. 
- Negative time intervals are set to nan. They cannot be real durations and or often caused by interviewers changing the tablet time. 
- All time intervals for events  `AnswerSet` and `AnswerRemoved` are summed for the item. 

Please note that `f__answer_duration` can only be an approximation of the actual time it took to answer an item. Due to the open navigation architecture of Survey Solutions, it is impossible to determine when a question was started/put into focus or ended/put out of focus. This is approximated with the timestamp of the previous event and the answer being set. Interviewers may do other things between these events without any active event being logged, e.g., confirm the response to the previous question. Likewise, short pauses logged while answering a question (e.g. when switching to the calculator app) are not attributed towards an item.

**Score**

For each `variable_name`, anomalies are detected separately on the lower and upper end using ...

The scores `s__answer_duration_lower` and `s__answer_duration_upper` are calculated as the share of all items set with lower or upper bound anomalies respectively.

<!-- @Gabriele, count on item level or is this this funky question_level thing again -->

## first_decimal

Identifies anomalies in the first two decimal digits in numeric values.

**Feature**

`f__first_decimal` contains the first two decimal digits of the response to all questions of type `NumericQuestion` in the microdata that are not integer questions (`IsInteger == False`).

**Score**

For variables with at least 3 different answer values and a minimum of 100 records in total, anomalies in `f__first_decimal` are identified by `variable_name` using COF 

As an example, if most answer values to a question contain decimals such as 0.25, 0.33, 0.5, 0.66, 0.75, a different value such as 0.47 would be flagged as anomaly. 

`s__first_decimal` is the share of numeric answers (filtered as above) with anomalies by interview.

## first_digit

**Feature**

`f__first_digit` contains the first digit of the response to all questions of type `NumericQuestion` in the microdata.

**Score**

can maybe use it for Benfords law.

## last_digit

**Feature**
`f__last_digit` contains the last digit (modulus of 10) of the response to all questions of type `NumericQuestion` in the microdata.

**Score**

in questions where we expect uniform distribution (e.g. height, weight, etc) and don't want to see rounding (0 and 5s), in others, e.g. monetary values we do not want to see values other than 0 if most of the others are 0.

## numeric_response

**Feature**

`f__numeric_response` contains the response to all questions of type `NumericQuestion` in the microdata.

**Score**

Note, numeric responses may contain "special values", often -99,-98 or 99, 999, 9999. They vary from survey to survey, but ideally are outside of the valid range. There might be multiple special values per question. They should be the same for the question and ideally for the entire questionnaire, but often people are sloppy. We can try to identify them automatically (outliers, that are the same number), or if not possible, ask this as input from the user. If they used the sepcial value feature from Survey Solutions, we might be able to extract it.

1. At a minimum automatically detect single variate outliers. Check distribution, if goes over orders of magnitude, take ln(). Work with iqrs or mad better than SD from mean as less outlier prone. Check outlier on item level, i.e. by VariableName and roster_level. You can also try to ignore roster_level and see if it makes a difference (i.e. compare all observations from one VariableName, independent from which roster they are from). 

2. Ideally, it would be great to also look into multivariate outlier detection, i.e. how weird is a response, given the other responses. Not clear how this could be automated, and how heavy this would be. 

3. Instead of only looking for outliers (just at the extremes), it would be great to also normalize the in a meaningful and outlier independent way, to get a measure of how extreme/non-extreme they are. The hypothesis is that cheaters attempt to avoid extreme values. 

## sequence_jump

Detects unusual patters in question answering sequence. 

**Feature**

`f__sequence_jump` counts the number of question sequences the interviewer jumped answering an item since the previous item. It is constructed the following way:

- For each item, the last interviewing event in paradata of type `AnswerSet` is kept. If an item was answered multiple times (e.g., re-answered later during interview), only the last event is considered. 
- For each item, the difference `diff` is calculated between the answer sequence (sequential number in paradata, sorted by column `order`) and the question sequence (sequence of question in the questionnaire). 
- The difference in `diff` to the previous item is calculated, allowing to compare if (groups of) questions have been answered in sequence even if previous sequence jumps occurred. 

`f__sequence_jump` take the value 0 if a question was answered directly after the previous question in terms of questionnaire sequence. Negative values correspond to a jump back in questionnaire sequence, while positive values correspond to a jump forward. If a questions was preceded by disabled questions (that could not be answered), this will be shown by a positive jump. Note that the first question on roster instances other than the first row start often has negative jumps, as interviewers "go back" a few questions in questionnaire sequence to start with the next roster item. 

**Score**

For each VariableName on the roster_level, there should be a set of legitimate jumps to get to this question, depending on the enablement conditions of the preceeding questions (usually positive, negative, only for first rowster rows). Check for unusual jumps. I think we can ignore unusual jumps if they were preceeded by an opposite jump of the same length (or +abs(1) jump), as it is just a second symptom of the same jump (assuming they go back to where they were previously. Unusual small positive numbers (i.e. interviewer skipped a question) but immediatelty followed by negative questions (i.e. interviewer noticed, went back and answered it) are not that bad and should maybe only be flagged if they occur frequently.

## string_length

**Feature**

`f__string_length` contains the length of the answer string to questions of type `TextQuestions` in the microdata.

**Score**

some string questions require detailed description, very short one might be indicative of not enough attention to detail.
Other specify fields (maybe identifiable as those questions that do not always have an answer), excessive use by one interviewer is not desirable

## time_changed

**Feature**

WHAT IS IT? COUNT? TOTAL IN SEC?

`f__time_changed` is constructed using active interviewing events in the paradata. Consecutive active events with a negative time difference lower than 180 seconds. Note that this excludes small negative time intervals (of under 2 minutes) generated by questions being answered after a GPS question has been clicked, but before the response to the GPS questions was recorded.

**Score**

Time changes are due to tablet time being reset, usually purposefully by the interviewer.

## gps

Detects anomalies in the location where GPS type questions were answered. 

[@Gabriele]: <> (Do we need the subfeatures in the yaml, always the same?)

**Feature**

Sub-features `gps_latitude`, `gps_longitude` and `gps_accuracy` are constructed for all questions of type `GpsCoordinateQuestion` in the microdata. Note that there may be none or multiple GPS question per interview and that they may refer to places other than the interview location, e.g., the location of the household plots. 

**Score**

`s__gps_proximity_count` for each unit returns number of other units within 10 meters radius + accuracy. Note maybe high accuracy might be an issue. In absolute numbers

`s__gps_spatial_extreme_outlier` find midpoint, median of lat and long, for each point calculate distance to midpoint, true if distance larger than 95 percentile of distancens + 30 kilometers (helps with high density cases)

`s__gps_spatial_outlier` exclude extreme outliers. if less than 10k records COF, otherwise LOF. COF is very memory demanding, seems to perform better, both are proximity based algorithms, COF works on connectivity based, while LOF. is binary  

0. any that are crazily far away like in another country or with 0 latitude and 0 longitude, are obviously with issues. 
1. In combination with f__latitude, identify clusters and mark outliers from the cluster, e.g. distance in SD to the cluster mid-point (mean lat and long). These can show that the interview was not collected at the location but sometimes is due to GPS not working (which should be fixed by the interviewer), and interviewers recording the GPS on the way home or in the evening (all of which is undesired behaviour). 
2. If some points are very close together (very low distance to other units within the cluster) with corresponding high accuracy (low number), and if this is not common, then this points at one or more interviewer taking interviews in the same place, which if not common is suspicious, as they might fabricate them from under the tree/restaurant/hotel/side of the road. 
3. Maybe explore variation from cluster location - date to identify those that are in one cluster for much longer than others (e.g. could be interviewer doing things from hotel).
4. If an outlier (let's say the point when they took the GPS in the car on the way back or in their hotel) was one of few Answers recorded, then it is more likely to be just a GPS issue (still bad enough, as we have then the wrong location for the household), but more or many Answers were set around the time where the outlier is, then more of the interview was done in a bad place, and this is extremely unlikely. 
5. We could use GPS cluster as an independent variable to control for some of the variation in other variables.

https://chat.openai.com/share/d09d54f5-91e0-44eb-bf19-efa7b408e873

Huge values (low accuracy) is indicative of wrong tablet settings. 

## pause_count

**Feature**

`f__pause_count` is the unit-level count of interviewing events of type `Resumed` or `Restarted` in the paradata, that are preceded by event `Paused` (which is also logged after event events `Completed`).

**Score**

`s__pause_count`, total number of pauses over f_number_answered

## pause_duration

**Feature**

`f__pause_duration` is constructed on the unit-level using interviewing events in the paradata. It is the sum of time difference in seconds between interviewing events of type `Resumed` or `Restarted` and preceding events of type `Paused` (which are also logged after event events `Completed`).

**Score**

`f__pause_duration` over elapsed.

ignore below
To control the sensibility of the outlier detection algorithm, pause duration is rounded to 2 hrs intervals for durations less then 24 hrs, and to full days for durations over 24 hrs. Anomalies are detected using [COF](https://github.com/yzhao062/pyod#thresholding-outlier-scores), which checks locally and is able to identify anomalies in the middle of a distribution. For example, pauses of 8, 10 or 12 hour length may be considered anomalous while shorter or longer pauses are not. 

`s__pause_duration` is calculated as a boolean that takes the value TRUE if an interview contained a pause of anomalous length, and FALSE otherwise.

## pause_list

**Feature**

`f__pause_list` is constructed on the unit-level using interviewing events in the paradata. It is a list of all the time difference in seconds between interviewing events of type `Resumed` or `Restarted` and preceding events of type `Paused` (which are also logged after event events `Completed`).

**Score**

## number_unanswered

**Feature**

**Score**

= feature

## number_answered

equals feature 

**Feature**

**Score**

## total_duration

Detects anomalies in the interview duration. 

**Feature**

`s__total_duration` is constructed on the unit level and contains an approximation of the total duration of active interviewing events. It is built as follows:

- 

**Score**

To control the sensibility of the outlier detection algorithm, `f__total_duration` is rounded to the next 10 minutes interval. 

## total_elapsed

**Feature**

**Score**

lower and upper outlier detection using ECOD, 
correlated up to a certain level, we take upper and lower outlier booleans to avoid corraltion with duration.

## single_question

**Feature**

**Score**

## multi_option_question

**Feature**
values selected for multi option questions 
**Score**

same as answer_position

# Not included

The following features have been extracted, but no utility has been found for them in the testing data (too few observations). They require more testing data and further investigation to be converted into scores.

## comment_length

**Feature**

`f__comment_length` contains the total length of comments set for an item, extracted from active interviewing events of type `CommentSet` in the paradata. 

**Rationale**

Very short comments (e.g. length <= 3) or comments only containing numeric values are often due to interviewers writing the answer to the question into the comment. This may be due to questionnaire mistake, in which case we should see comments frequently for the item, or interviewers being confused, which we would like to flag. Longer comments may provide more information.

## comment_set

**Feature**

`f__comment_set` contains the total number of comments set for an item, extracted from active interviewing events of type `CommentSet` in the paradata. 

**Rationale**

In principle, comments should provide additional information to the Supervisor/HQ/data user, e.g., when the interviewer cannot solve a problem or wants to confirm a unusual answer. Item level anomalies from other features with comments set for the same item may be less of an issue. If comments are frequent, the absence of comments may be suspicious.

## comment_duration

**Feature**

`f__comment_duration` is constructed similar to [answer_duration](#answerduration), summing instead the intervals for all events of type `CommentSet`.

