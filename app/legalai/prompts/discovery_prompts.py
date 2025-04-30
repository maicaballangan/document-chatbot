NORMAL_ANSWER_PROMPT = """You are a client who has to answer to the plaintiff or defendant about issues or pieces of evidence related to the 
litigation {context}. You have a need related to litigation and need to provide information so that the plaintiff or
defendant can prosecute or defend. Follow the guidelines to make output.
"""

EXTRACT_QUESTION_FROM_INTERROGATIVE_DOCUMENT_PROMPT = """I need you to detect whether the attached document is an interrogative document or not. The definition of an interrogative file is:
    - Legal cases involve two parties: the plaintiff and the defendant.
    - Communication between these parties happens through a formal document submitted to the court.
    - This document can include instructions from the plaintiff or an answer from the defendant.
    - Within the document, specific sections called "INSTRUCTION QUERIES" detail these instructions or answers.
    - Each "INSTRUCTION QUERY" is identified by a number and separated from others by blank lines and ignore all responses

If it is an interrogative document, you need to return list of INSTRUCTION QUERY inside that in json format. The Json is a list of string, where each string is INSTRUCTION QUERY content.
If not, just return 'This document is not an interrogative document'
"""

NEW_EXTRACT_QUESTION_FROM_INTERROGATIVE_DOCUMENT_PROMPT = """I need you to detect 
whether the attached document is an interrogative document or not. The definition of an 
interrogative file is: 
- Legal cases involve two parties: the plaintiff and the defendant. 
- Communication between these parties happens through a formal document submitted to the court. 
- This document can include instructions from the plaintiff or an answer from the defendant. 
- Within the document, specific sections called 'INSTRUCTION QUERIES' detail these instructions, answers and maybe questions. 
- Each 'INSTRUCTION QUERY' is identified by a number and separated from others by blank lines and ignore all responses. 

If the document is not an interrogative document, just return 'This document is not an 
interrogative document'. If it is an interrogative document, you need to return only 
list of INSTRUCTION QUERY inside that in json format. The JSON is a list of string, 
where each string is INSTRUCTION QUERY content."""


EXTRACT_CASE_DETAIL = """answering below questions and return output:      
1. Please identify value of case number.      
2. Please identify value of plaintiff's name.      
3. Please identify value of defendant's name.      
Your output MUST be JSON format! We need to send the output to an API, so please 
provide a JSON output as follows where you indicate which property is true:      
{\"case_number\": '',\"plaintiff_name\": '',\"defendant_name\": '',}"""

ANSWER_WITH_OBJECTION_LIST_PROMPT = """Here is this list of objections following this format on each item: 'NAME': 'DESCRIPTION' \n
{objection_list}

We have 2 definitions: 
    + SELECTED OBJECTIONS: the list of objections above
    + ANSWER: the answer that you must find based on the question, the documents, the 'FORCED OBJECTION'.
The output must be following format:
    SELECTED OBJECTIONS
    ANSWER

In output must list all objection in SELECTED OBJECTIONS
For example, if SELECTED OBJECTIONS contain three items, the output must be:
SELECTED OBJECTIONS
- NAME of objection 1: DESCRIPTION of objection 1
- NAME of objection 2: DESCRIPTION of objection 2
- NAME of objection 3: DESCRIPTION of objection 3
ANSWER: the answer that you find.
"""

NORMAL_ANSWER_AUTO_OBJECTION_PROMPT = """We have two definitions: 
+ AUTO OBJECTIONS: any objections that you feel that is relevant to that question.
+ Answer: the answer that you must find based on the question, the documents, the Objection, and the Auto Objections.
The output must be following format:
    AUTO OBJECTIONS
    ANSWER
For example, if AUTO OBJECTIONS contain three items, the output must be:
AUTO OBJECTIONS
- NAME of objection 1: DESCRIPTION of objection 1
- NAME of objection 2: DESCRIPTION of objection 2
- NAME of objection 3: DESCRIPTION of objection 3
ANSWER: the answer that you find.
"""

ANSWER_AUTO_OBJECTION_LIST_PROMPT = """Here is this list of objections following this format on each item: 'NAME': 'DESCRIPTION' \n
{objection_list}

We have three definitions: 
    + SELECTED OBJECTIONS: the list of objections above 
    + AUTO OBJECTIONS: any objections that you feel that is relevant to that question.
    + Answer: the answer that you must find based on the question, the documents, the Objection, and the Auto Objections.
    The output must be following format:
        SELECTED OBJECTIONS
        AUTO OBJECTIONS
        ANSWER
    In output must list all objection in SELECTED OBJECTIONS
    For example, if SELECTED OBJECTIONS contain three items, and AUTO OBJECTIONS contain two items ,the output must be:
    SELECTED OBJECTIONS
    - NAME of objection 1: DESCRIPTION of objection 1
    - NAME of objection 2: DESCRIPTION of objection 2
    - NAME of objection 3: DESCRIPTION of objection 3
    AUTO OBJECTIONS
    - NAME of objection 4: DESCRIPTION of objection 4
    - NAME of objection 5: DESCRIPTION of objection 5
    ANSWER: the answer that you find.
"""
