
## f__string_length

<span style="font-size: larger; font-weight: bold;">Scope</span>

Answers to TextQuestions in the microdata

<span style="font-size: larger; font-weight: bold;">Built</span>

length of string answer

<span style="font-size: larger; font-weight: bold;">Score</span>

some string questions require detailed description, very short one might be indicatice of not enough attention to detail.
Other specify fields (maybe identifiable as those questions that do not always have an answer), exessive use by one interviewer is not desirable

## f__numeric_response

**Scope**

Answers to NumericQuestion in the microdata

**Built**

Response for numeric questions

**Score**

Note, numeric responses may contain "special values", often -99,-98 or 99, 999, 9999. They vary from survey to survey, but ideally are outside of the valid range. There might be multiple special values per question. They should be the same for the question and ideally for the entire questionnaire, but often people are sloppy. We can try to identify them automatically (outliers, that are the same number), or if not possible, ask this as input from the user. If they used the sepcial value feature from Survey Solutions, we might be able to extract it.

1. At a minimum automatically detect single variate outliers. Check distribution, if goes over orders of magnitude, take ln(). Work with iqrs or mad better than SD from mean as less outlier prone. Check outlier on item level, i.e. by VariableName and roster_level. You can also try to ignore roster_level and see if it makes a difference (i.e. compare all observations from one VariableName, independent from which roster they are from). 

2. Ideally, it would be great to also look into multivariate outlier detection, i.e. how weird is a response, given the other responses. Not clear how this could be automated, and how heavy this would be. 

3. Instead of only looking for outliers (just at the extremes), it would be great to also normalize the in a meaningful and outlier independent way, to get a measure of how extreme/non-extreme they are. The hypothesis is that cheaters attempt to avoid extreme values. 

## f__first_digit

**Scope**

Answers to NumericQuestion in the microdata

**Built**

first digit

**Score**

can maybe use it for Benfords law.

## f__last_digit

**Scope**

Answers to NumericQuestion in the microdata

**Built**

last digit, i.e. modulus of 10

**Score**

in questions where we expect uniform distibution (e.g. height, weight, etc) and don't want to see rounding (0 and 5s), in others, e.g. monetary values we do not want to see values other than 0 if most of the others are 0.

## f__first_decimal

**Scope**

Answers to NumericQuestion in the microdata, where question property 'IsInteger' == False

**Built**

first decimal digit

**Score**

same as f__last_digit

## f__answer_position

**Scope**

Answers to SingleQuestion in the microdata, for questions with fixed answer options (not linked) and > 2 answer options.

**Built**

relative position of the selected answer, ranging from 0 (first answer selected) to 1 (last answer selected), in intervals of 1/N answer options available

**Score**

straightlining (selecting the same answer options in repeated rating questions), or selection of non-extreme values in fabrication, lasting/firsting

## f__answers_selected

**Scope**

Answers to MultyOptionsQuestion and TextListQuestion in the microdata

**Built**

number of answers selected in a multi-answer, number of YES a YesNo question, number of items listed in a list question.

**Score**

detect unusual high or low number of item selection

## f__share_selected

**Scope**

Answers to MultyOptionsQuestion and TextListQuestion in the microdata, for questions with fixed answer options (not linked)

**Built**

share between answers selected, and available answers (only for unlinked questions)

**Score**

detect unusual high or low number of item selection

## f__latitude

**Scope**

Answers to GpsCoordinateQuestion in the microdata

**Built**

Latitude from the GPS question. Note that ther may be none or multiple GPS question per unit. They may refer to different places, so can legitimatyl be apart, e.g. the coordinates of the household plots. 

**Score**

0. any that are crazily far away like in another country or with 0 latitude and 0 longitude, are obviously with issues. 
1. In combination with f__latitude, identify clusters and mark outliers from the cluster, e.g. distance in SD to the cluster mid point (mean lat and long). These can show that the interview was not colllected at the location but sometimes is due to GPS not working (which should be fixed by the interviewer), and interviewers recording the GPS on the way home or in the evening (all of which is undesired behaviour). 
2. If some points are very close together (very low distance to other units within the cluster) with corresponding high accuracy (low number), and if this is not common, then this points at one or more interviewer taking interviews in the same place, which if not common is suspicious, as they might fabricate them from under the tree/restraurant/hotel/side of the road. 
3. Maybe explore variation from cluster location - date to identify those that are in one cluster for much longer than others (e.g. could be interviewer doing things from hotel).
4. If an outlier (let's say the point when they took the GPS in the car on the way back or in their hotel) was one of few Answers recorded, then it is more likely to be just a GPS issue (still bad enough, as we have then the wrong location for the household), but more or many Answers were set around the time where the outlier is, then more of the interview was done in a bad place, and this is extremely unlikely. 
5. We could use GPS cluster as an independent variable to control for some of the variation in other variables.

https://chat.openai.com/share/d09d54f5-91e0-44eb-bf19-efa7b408e873

## f__longitude

**Scope**

Answers to GpsCoordinateQuestion in the microdata

**Built**

Longitude from the GPS question

**Score**

see above

## f__accuracy

**Scope**

Answers to GpsCoordinateQuestion in the microdata

**Built**

Accuracy from the GPS question

**Score**

Huge values (low accuracy) is indicative of wrong tablet settings. 

## f__duration_answer

**Scope**

Interviewing events in paradata of type 'AnswerSet' and 'AnswerRemoved'

**Built**

Total duration for 'AnswerSet' and 'AnswerRemoved' events. Only active interviewing events are kept. For every event, the time interval to the previous event (by variable 'order') is calculated. Negative time intervals are set to nan, as they are caused by changes of the tablet time. All time intervals for events  'AnswerSet' and 'AnswerRemoved' are summed for the item. 

**Score**

nan

## f__duration_comment

**Scope**

Interviewing events in paradata of type 'CommentSet'

**Built**

Total duration for 'CommentSet' events. Only active interviewing events are kept. For every event, the time interval to the previous event (by variable 'order') is calculated. Negative time intervals are set to nan, as they are caused by changes of the tablet time. All time intervals for events  'CommentSet' are summed for the item. 

**Score**

nan

## f__time_changed

**Scope**

Active interviewing events in paradata.

**Built**

Consecutive active events with negative time difference lower than 120 seconds. Note that this excludes small negative time intervals (of under 2 minutes) generated by questions being answered after a GPS question has been clicked, but before the response to the GPS questions was recorded.

**Score**

Time changes are due to tablet time being reset, usually purposefully by the interviewer.

## f__previous_question

**Scope**

Last interviewing event in paradata of type 'AnswerSet' event. If an item was answered multiple times, only the last event is considered.

**Built**

The question that was answered prior, i.e. the 'variable_name' of the previous (by variable 'order') 'AnswerSet' event, ignoring repeated events for the same item. 

**Score**

An alternative to f__sequence_jump. Can be used to identify unusual answering sequences, e.g. by identifying unusal previous question_answer combinations for a question.

## f__previous_answer

**Scope**

Last interviewing event in paradata of type 'AnswerSet' event. If an item was answered multiple times, only the last event is considered.

**Built**

The answer that was recorded (last) at the prior question, i.e. the 'variable_name' of the previous (by variable 'order') 'AnswerSet' event, ignoring repeated events for the same item. 

**Score**

nan

## f__previous_roster

**Scope**

Last interviewing event in paradata of type 'AnswerSet' event. If an item was answered multiple times, only the last event is considered.

**Built**

The roster level at which the prior question was recorded, i.e. the 'variable_name' of the previous (by variable 'order') 'AnswerSet' event, ignoring repeated events for the same item. 

**Score**

nan

## f__sequence_jump

**Scope**

Last interviewing event in paradata of type 'AnswerSet' event. If an item was answered multiple times, only the last event is considered.

**Built**

Difference between actual answer sequence (considering last 'AnswerSet' event in paradata) and question sequence (sequence as in the questionnaire), relative to previous question, allowing to compare if (groups of) questions have been answered in sequence even if previous jumps occured. Value 0 means that a question was answered directly after the previous question in terms of questionnaire sequence. Negative values correspond to a jump back in questionnaire order, while positive values correspond to a jump forward. Note that the first question on roster instances other than the first row start with negative jumps. If a questions was preceeded by disabled questions (that could not be answered), this will be shown by a positive skip. If a question was answered multiple times, only the relative sequence of the last event is considered.

**Score**

For each VariableName on the roster_level, there should be a set of legitimate jumps to get to this question, depending on the enablement conditions of the preceeding questions (usually positive, negative, only for first rowster rows). Check for unusual jumps. I think we can ignore unusual jumps if they were preceeded by an opposite jump of the same length (or +abs(1) jump), as it is just a second symptom of the same jump (assuming they go back to where they were previously. Unusual small positive numbers (i.e. interviewer skipped a question) but immediatelty followed by negative questions (i.e. interviewer noticed, went back and answered it) are not that bad and should maybe only be flagged if they occur frequently.

## f__half_hour

**Scope**

Last interviewing event in paradata of type 'AnswerSet' event. If an item was answered multiple times, only the last event is considered.

**Built**

Extracted half hour intervals from the hour and minutes of the timestamp.

**Score**

nan

## f__half_hour_prob_norm

**Scope**

Last interviewing event in paradata of type 'AnswerSet' event. If an item was answered multiple times, only the last event is considered.

**Built**

Share of 'AnswersSet' events occuring in half-hour intervals for entire survey. Distance between shares of the highest interval and the interval, over the share of the highest interval.

**Score**

nan

## f__in_working_hours

**Scope**

Last interviewing event in paradata of type 'AnswerSet'. If an item was answered multiple times, only the last event is considered.

**Built**

nan

**Score**

nan

## f__answer_removed

**Scope**

All interviewing event in paradata of type 'AnswerRemoved'.

**Built**

Count of events 'AnswerRemoved', either from interviewer actively removing an answer or by the system removing answers as a consequence by an interviewer action. A changes to the response of a questions linked to a roster may produce multiple such events. The item may no longer exist in the microdata.

**Score**

Removing of answers to linked questions may be indicative of interviewers cutting the interview length, especially at the beginning of the survey

## f__answer_changed

**Scope**

Active interviewing events of type 'AnswerSet' in the paradata.

**Built**

For questions with single answer, the answer value is compared to the previous answer values for the item (if it exists) and the event counted if different. For questions of type 'MultyOptionsQuestion' and 'TextListQuestion', events are counted if the set of answers no longer contains any elements from the previous set of answers. This can occur if an answer option has been unselected or removed, or if the text of a list item has been removed. For multiselect questions with yes/no mode, the sets of Yes and No answers are evaluated separatly and events counted if an answer option has been removed or changed from Yes to No or vice versa.

**Score**

Removing of answers to linked questions may be indicative of interviewers cutting the interview length, especially at the beginning of the survey

## f__comment_set

**Scope**

Active interviewing events of type 'CommentSet' in the paradata. 

**Built**

Count of comments set

**Score**

in principle, comments should give additional information e.g. when a problem cannot be solved. issues from other features with comments may be less of an issue. If comments are frequent, the absence of comments may be suspicious.

## f__comment_length

**Scope**

Active interviewing events of type 'CommentSet' in the paradata. 

**Built**

Total length of comments.

**Score**

very short comments (e.g. length <= 3) is often due to interviewers writing the answer. this may be due to a mistake of the questionnaire, in which case we should see it frequently for the item, or interviewers may be confused, which we would like to flag. Longer comments may provide more information.

## f__outstanding_error

**Scope**

nan

**Built**

nan

**Score**

nan

## f__answer_missing

**Scope**

nan

**Built**

nan

**Score**

nan

## nan

**Scope**

nan

**Built**

nan

**Score**

nan

## nan

**Scope**

nan

**Built**

nan

**Score**

nan

## nan

**Scope**

Unused events, explore if useful: QuestionDeclaredInvalid, QuestionDeclaredValid, QuestionDisabled, QuestionEnabled, VariableDisabled, VariableEnabled, VariableSet

**Built**

nan

**Score**

nan

## nan

**Scope**

Unused question types:
datetime questions
variables

**Built**

nan

**Score**

nan

## nan

**Scope**

nan

**Built**

nan

**Score**

nan
