
This chapter describes the construction of all features and scores. 

# Paradata based features

## f__days_from_start
[@Gabriele]: <> (inconsitent naming, how does it enter)

## answer_time_set
[@Gabriele]: <> (
- Let's rename to answer_hour or event_hour,
- scope not clear to me, should be from active, looks like it is from paradata,
- should we adjust for TZ?
- you can delete the the half_hour feature)

Captures active interviewing events during unusual hours of the day.


**Feature**

`f__answer_time_set` is the hour of the day from the paradata timestamp, rounded to half-hour intervals. No timezone adjustments are done. It is constructed on the item level for all active interviewing actions performed by the interviewer in the paradata.

**Score**

Anomalies in `f__answer_time_set` across all events are detected using the [ECOD](https://arxiv.org/pdf/2201.00382.pdf), a fast, non-parametric and easy-to-interpret algorithm using cumulative distribution functions. The `contamination` parameter is set to 0.11 by default (based on testing data) and can be adjusted in `environment/main.yaml`. Increase it to be stricter, decrease to be more lenient.

`s__answer_time_set` is the share of anomalies per interview. The value ranges from 0 (whole interview was conducted during usual hours of the day) to 1 (whole interview during unusual hours of the day). Please note that the score is treating all days equal and is not dependent on the date nor the day-of-the-week.   

## answer_changed

Captures unusual number of changes to question answers.

**Feature**

`f__answer_changed` is constructed using all active interviewing events of type `AnswerSet` in the paradata. It contains the number of times the answer to an item has been changed. Changes are counted as follows:

- For questions with single answer, the answer value is compared to the previous answer values for the item (if it exists) and the event counted if different. 
- For questions of type `MultyOptionsQuestion` and `TextListQuestion`, events are counted if the set of answers no longer contains any elements from the previous set of answers. This can occur if an answer option has been unselected or removed, or if the text of a list item has been removed. 
- For multi-answer questions with Yes/No mode, the sets of Yes and No answers are evaluated separately and events counted if an answer option has been removed or changed from Yes to No or vice versa.

**Score**

[@Gabriele]: <> (Let's talk about item vs question level again)

Anomalies in `f__answer_changed` are detected using the [ECOD](https://arxiv.org/pdf/2201.00382.pdf), a fast, non-parametric and easy-to-interpret algorithm using cumulative distribution functions. The `contamination` parameter is set to 0.10 by default (based on testing data) and can be adjusted in `environment/main.yaml`. Increase it to be stricter, decrease to be more lenient. Anomalies are detected on the question level (`variable_name`) to reduce disaggregation. Each question is considered to have an anomaly if an anomaly was detected for the question on any `roster_level`. 


`s__answer_changed` is the share of questions answered with anomalies in `f__answer_changed` per interview. The value ranges from 0 (no anomalies) to 1 (hypothetical, only anomalies). An anomaly is an unusual high (or low) number of changes to the answer of a question. E.g., if it is common for the answer to a member list question to be changed 0-2 times, these would not be considered as anomalies, but an interview with 5 answer changes would. 

## answer_removed

Captures unusual number of times answers were removed for a question.

**Feature**

`f__answer_removed` is constructed using interviewing events in the paradata. It counts the number of times an event of type `AnswerRemoved` was logged for an item. These can be due to either an interviewer actively removing the answer to an item or due to Survey Solutions removing answers as a consequence of an interviewer action. A changes to the response of a question linked to a roster may produce multiple such events. The item may no longer exist in the microdata.

[@Gabriele]: <> (The item may no longer exist in the microdata. How do we deal with them?)

**Score**

[@Gabriele]: <> (Let's talk about item vs question level again)

Anomalies in `f__answer_removed` are detected using the [ECOD](https://arxiv.org/pdf/2201.00382.pdf), a fast, non-parametric and easy-to-interpret algorithm using cumulative distribution functions. The `contamination` parameter is set to 0.10 by default (based on testing data) and can be adjusted in `environment/main.yaml`. Increase it to be stricter, decrease to be more lenient. Anomalies are detected on the question level (`variable_name`) to reduce disaggregation. Each question is considered to have an anomaly if an anomaly was detected for the question on any `roster_level`. 

`s__answer_removed` is the share of questions answered with anomalies in `f__answer_removed` per interview. The value ranges from 0 (no anomalies) to 1 (hypothetical, only anomalies). An anomaly is an unusual high (or low) number of times the answers has been removed for a question in an interview. 

## answer_position

Detects XYZ...

**Feature**

`f__answer_position` is constructed on the item level for all answered questions of type `SingleQuestion` in the microdata with fixed answer options (question is not linked), more than 2 answer options, and are not of type Combobox. It contains the relative position of the selected answer, ranging from 0 (answer on top was selected) to 1 (answer on bottom selected), in intervals of 1/N answer options available. 

**Score**

straightlining (selecting the same answer options in repeated rating questions), or selection of non-extreme values in fabrication, lasting/firsting

## answers_selected

Detects XYZ...

**Feature**
`f__answers_selected` is constructed on the item level for all answered questions of type `MultyOptionsQuestion` and `TextListQuestion` in the microdata. It contains:

- For YesNo question, the number of YES options selected.
- For other multi-answer questions, the number of answers selected.
- For list questions, the number of items listed.

**Score**

detect unusual high or low number of item selection

## answer_share_selected

Detects XYZ...

**Feature**

**Score**

## answer_duration

**Feature**

`f__answer_duration` is constructed on the item level using active interviewing events in the paradata. It contains the total duration in seconds of events of type `AnswerSet` and `AnswerRemoved` associated with an item. It is built as follows:

- Only active interviewing events are kept. This removes events generated by Survey Solutions and events that cannot be attributed to an item. 
- For every event, the time interval to the previous event (by column `order`) is calculated. 
- Negative time intervals are set to nan. They cannot be real durations and or often caused by interviewers changing the tablet time. 
- All time intervals for events  `AnswerSet` and `AnswerRemoved` are summed for the item. 

Please note that `f__answer_duration` can only be an approximation of the actual time it took to answer an item. Due to the open navigation architecture of Survey Solutions, it is impossible to determine when a question was started/put into focus or ended/put out of focus. This is approximated with the timestamp of the previous event and the answer being set. Interviewers may do other things between these events without any active event being logged, e.g., confirm the response to the previous question. Likewise, short pauses logged while answering a question (e.g. when switching to the calculator app) are not attributed towards an item.

**Score**

## comment_length

**Feature**

`f__comment_length` contains the total length of comments set for an item, extracted from active interviewing events of type `CommentSet` in the paradata. 

**Score**

very short comments (e.g. length <= 3) is often due to interviewers writing the answer. this may be due to a mistake of the questionnaire, in which case we should see it frequently for the item, or interviewers may be confused, which we would like to flag. Longer comments may provide more information.

## comment_set

**Feature**

`f__comment_set` contains the total number of comments set for an item, extracted from active interviewing events of type `CommentSet` in the paradata. 


**Score**

in principle, comments should give additional information e.g. when a problem cannot be solved. issues from other features with comments may be less of an issue. If comments are frequent, the absence of comments may be suspicious.

## comment_duration

**Feature**

`f__comment_duration` is constructed similar to [answer_duration](#answerduration), summing instead the intervals for all events of type `CommentSet`.

**Score**

## first_decimal

**Feature**

`f__first_decimal` contains the first decimal digit of the response to all questions of type `NumericQuestion` in the microdata that are not integer questions (`IsInteger == False`).

**Score**

same as f__last_digit

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

some string questions require detailed description, very short one might be indicatice of not enough attention to detail.
Other specify fields (maybe identifiable as those questions that do not always have an answer), exessive use by one interviewer is not desirable

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

Sub-features `gps_latitude`, `gps_longitude` and `gps_accuracy` are constructed for all questions of type `GpsCoordinateQuestion` in the microdata.

Latitude from the GPS question. Note that there may be none or multiple GPS question per unit. They may refer to different places, so can legitimatyl be apart, e.g. the coordinates of the household plots. 

**Score**

0. any that are crazily far away like in another country or with 0 latitude and 0 longitude, are obviously with issues. 
1. In combination with f__latitude, identify clusters and mark outliers from the cluster, e.g. distance in SD to the cluster mid point (mean lat and long). These can show that the interview was not colllected at the location but sometimes is due to GPS not working (which should be fixed by the interviewer), and interviewers recording the GPS on the way home or in the evening (all of which is undesired behaviour). 
2. If some points are very close together (very low distance to other units within the cluster) with corresponding high accuracy (low number), and if this is not common, then this points at one or more interviewer taking interviews in the same place, which if not common is suspicious, as they might fabricate them from under the tree/restraurant/hotel/side of the road. 
3. Maybe explore variation from cluster location - date to identify those that are in one cluster for much longer than others (e.g. could be interviewer doing things from hotel).
4. If an outlier (let's say the point when they took the GPS in the car on the way back or in their hotel) was one of few Answers recorded, then it is more likely to be just a GPS issue (still bad enough, as we have then the wrong location for the household), but more or many Answers were set around the time where the outlier is, then more of the interview was done in a bad place, and this is extremely unlikely. 
5. We could use GPS cluster as an independent variable to control for some of the variation in other variables.

https://chat.openai.com/share/d09d54f5-91e0-44eb-bf19-efa7b408e873

Huge values (low accuracy) is indicative of wrong tablet settings. 

## pause_count

**Feature**

`f__pause_count` is the unit-level count of interviewing events of type `Resumed` or `Restarted` in the paradata, that are preceded by event `Paused` (which is also logged after event events `Completed`).

**Score**

## pause_duration

**Feature**

`f__pause_duration` is constructed on the unit-level using interviewing events in the paradata. It is the sum of time difference in seconds between interviewing events of type `Resumed` or `Restarted` and preceding events of type `Paused` (which are also logged after event events `Completed`).

**Score**

## pause_list

**Feature**

`f__pause_list` is constructed on the unit-level using interviewing events in the paradata. It is a list of all the time difference in seconds between interviewing events of type `Resumed` or `Restarted` and preceding events of type `Paused` (which are also logged after event events `Completed`).

**Score**

## number_unanswered

**Feature**

**Score**

## number_answered

**Feature**

**Score**


## total_duration

**Feature**

**Score**


## total_elapsed

**Feature**

**Score**

## single_question

**Feature**

**Score**

## multi_option_question

**Feature**

**Score**


# TO BE DONE


## f__share_selected

**Scope**

Answers to MultyOptionsQuestion and TextListQuestion in the microdata, for questions with fixed answer options (not linked)

**Feature**

share between answers selected, and available answers (only for unlinked questions)

**Score**

detect unusual high or low number of item selection



