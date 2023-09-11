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

Type 1 Score. Anomalies within `f__answer_changed` are detected using [ECOD](https://arxiv.org/pdf/2201.00382.pdf), an efficient, non-parametric algorithm that leverages cumulative distribution functions. The contamination level is determined automatically by default, but it can also be [set manually](README.md#Advanced-Use) if required. <!-- is below correct?, no, checkeing for anomalis without roster level, but aggregating on ratio of items with anomalies --> Anomalies are detected on the question level (`variable_name`) to reduce disaggregation. Each question is considered to have an anomaly if an anomaly was detected for the question on any `roster_level`. 

`s__answer_changed` is the share of questions answered <!--answers or question?? --> with anomalies in `f__answer_changed` per interview. The value ranges from 0 (no anomalies) to 1 (hypothetical, only anomalies). An anomaly is an unusual high (or low) frequency of changes to the answer of a question. E.g., if it is commonplace for a member list question to be changed 0-2 times, these changes won't be classified as anomalies. However, the question may be deemed anomalous if it has been changed 5 times. 

## answer_removed

This feature captures atypical frequencies of answer removals.

**Feature**

`f__answer_removed` is constructed using interviewing events in the paradata. It counts the number of times an event of type `AnswerRemoved` was logged for an item. These events can result from an interviewer actively deleting an answer or from Survey Solutions removing answers due to specific interviewer actions. Modifying the response of a question linked to a roster can trigger multiple such events.

**Score**

Type 1 Score. Anomalies in `f__answer_removed` are detected using [ECOD](https://arxiv.org/pdf/2201.00382.pdf), an efficient, non-parametric algorithm that leverages cumulative distribution functions. The contamination level is determined automatically by default, but it can also be [set manually](README.md#Advanced-Use) if required. <!-- Below still the case, as answers changed --> Anomalies are detected on the question level (`variable_name`) to reduce disaggregation. Each question is considered to have an anomaly if an anomaly was detected for the question on any `roster_level`. 

`s__answer_removed` is the share of questions in an interview that show anomalies in `f__answer_removed`. The score's range is from 0 (indicating no anomalies) to 1 (a theoretical scenario denoting only anomalies). An anomaly refers to an unusually high or low frequency of answer removals for a question. 

## single_question

call it single_question 

This feature identifies the tendency to repeatedly select the same answer options in single-select questions.

**Feature**

`f__single_question` is constructed on the item level for all questions of type `SingleQuestion` in the microdata with fixed answer options (question is not linked), 2 or more answer options, and which are not of the Combobox type. The feature indicates the relative position of the chosen answer: a value of 0 means the top answer was selected, and a value of 1 means the bottom-most answer was selected. The feature is scaled in intervals of 1/N, where N is the total number of answer options available.

<!-- is this still using position or actual values? -->

**Score**

Type 3 Score. `s__single_question` represents the proportion of questions for a given interviewer where there's a noticeable pattern in selecting similar or identical answer options compared to other interviewers. The score is derived by:

- Identifying those `variable_name` for each interviewer with observations exceeding five times the number of available answer options.
- Computing the entropy for these `variable_name` for each interviewer, capturing the diversity in their answers.
- Designating a `variable_name` as anomalous for an interviewer if its entropy is less than half the median entropy value compared to other interviewers.
- Calculating the share of anomalous variables over all variables for which entropy was assessed.

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

This feature highlights anomalous durations, either too short or too long, for individual questions.

**Feature**

`f__answer_duration` is constructed at the item level using active interviewing events from the paradata. It represents the total duration, in seconds, for events of type `AnswerSet` and `AnswerRemoved` linked to an item. It is constructed by:

- Keeping only active interviewing events. This removes events generated by Survey Solutions and events that cannot be attributed to an item. 
- For every event, computing the time interval to its preceding event (sorted by column `order`). 
- Assign a value of NaN (Not a Number) to negative time intervals, which are unrealistic durations often resulting from interviewers altering the tablet's time settings.
- Sum all time intervals for `AnswerSet` and `AnswerRemoved` events related to the item. 

It's important to understand that `f__answer_duration` is an approximation of the actual time taken to answer an item. The open navigation design of Survey Solutions makes it challenging to pinpoint when a question is activated or deactivated. This is approximated using the timestamp of the preceding event and the time the answer is set. During these intervals, interviewers might undertake other tasks without logging any active event, like confirming the response to a prior question. Similarly, brief pauses recorded while administering a question (e.g., when accessing a calculator app) aren't allocated to a particular item.

**Score**

Type 1 Score. First, anomalies in `f__answer_duration` are identified using [ECOD](https://arxiv.org/pdf/2201.00382.pdf), an efficient, non-parametric algorithm that leverages cumulative distribution functions. Anomalies are detected on the item-level by `variable_name` <!-- also by interviewer? -->.

Subsequently, two scores, `s__answer_duration_lower` and `s__answer_duration_upper` are computed. They represent the share of items in an interview with anomalies at the lower or upper bounds respectively. Lower and upper end anomalies are treated separately as they indicate different potential undesired behaviours. Lower end anomalies point at interviewers rushing or fabricating data, upper end at interviewer struggling (or interview/respondent effects). 

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

This feature identifies anomalies in the recorded locations for GPS-type questions.

**Feature**

Sub-features `gps_latitude`, `gps_longitude` and `gps_accuracy` are constructed for all items of type GpsCoordinateQuestion in the microdata. It's important to note that there might be no or multiple GPS questions within an interview. Additionally, these GPS questions could refer to various places beyond the interview location, such as the location of household plots. 

**Score**

Type 1 Score. Three distinct scores are derived:

`s__gps_proximity_count`: Represents the total number of items located within a radius of 10 meters, plus the accuracies of both points, of any other points recorded within an interview. Note that high accuracy values could skew this score. The score essentially detects anomalies in location density. For instance, in stratified household surveys, numerous points at the same location could be suspicious. Conversely, in institutional surveys (like school or health center surveys), a high count is expected since interviews are usually conducted at the same location.

`s__gps_extreme_outlier` contains the count of extreme outlier locations in an interview. It indicates locations that were recorded outside the survey area. The score is derived by:
- Computing the median longitude and latitude across all locations to establish a midpoint.
- Determining the distance of each point to this midpoint.
- Flagging points as anomalous if their distance to the midpoint exceeds the 95th percentile of all distances by over 30 kilometers (accounting for high-density cases).<!-- would not an MAD or IQR range be better, if we have no extreme outliers and widespread survey, this approach may pick up the edges, no? --> 
- Counting these anomalous points within an interview. The score is treated in absolute terms, ensuring that interviews with any extreme outliers are deemed suspicious without being offset by other non-anomalous points within the same interview.

`s__gps_outlier` counts outlier locations within an interview. While some outliers might indicate legitimately remote locations, many arise from interviewers recording the GPS locations while on the move or at their accommodation. The score is derived by:
- Excluding points flagged as extreme outliers. 
- Detecting anomalies using [COF](https://github.com/yzhao062/pyod#thresholding-outlier-scores) for datasets containing fewer than 10k records, and [LOF](https://github.com/yzhao062/pyod#thresholding-outlier-scores) for larger datasets. Both methods are proximity-based, with COF generally performing better, albeit with higher memory demands.
- Counting these anomalous points within an interview. The score is treated in absolute terms, ensuring that interviews with any extreme outliers are deemed suspicious without being offset by other non-anomalous points within the same interview.

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

## number_unanswered

This feature quantifies the total number of unanswered questions in an interview.

**Feature**

`s__number_unanswered` represents the count of unanswered questions (values [-999999999, '##N/A##']) in the microdata that correspond to interviewing events in the paradata <!-- thinking about this again, the filter of only take observations that also exist in the paradata does not make sense for this feature (I think), maybe we drop the whole feature?? -->. Multi-select questions contribute as a single count. Survey Solution variables are excluded. 

**Score**

Type 2 Score.  `s__number_unanswered` is directly equated to `f__number_unanswered`.

## number_answered

This feature quantifies the total number of answers recorded in an interview.

**Feature**

`s__number_answered` represents the count of answers recorded in the microdata that correspond to interviewing events in the paradata. Multi-select questions contribute as a single count. Answers with values [-999999999, '##N/A##'] are excluded since they signify questions that were enabled but remain unanswered. Survey Solution variables and system generated variables are also excluded. 

**Score**

Type 2 Score.  `s__number_answered` is directly equated to `f__number_answered`.

<!-- should we also round here to e.g. interval of 10, like for duration, to control for sensibility? -->

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

Type 2 Score. `s__total_duration` is computed by rounding `f__total_duration to the next 10 minutes interval. This is done to control sensibility of the algorithm used to aggregate scores.

## total_elapsed

**Feature**
`f__total_elapsed`
**Score**

lower and upper outlier detection using ECOD, 
correlated up to a certain level, we take upper and lower outlier booleans to avoid corraltion with duration.

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

