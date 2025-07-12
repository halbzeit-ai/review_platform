import os
import json
from PIL import Image
from io import BytesIO
import ollama
from ollama import chat
from pydantic import BaseModel
import subprocess
import time

def restart_ollama_service(): 
    try: 
        # Stop the Ollama service 
        # subprocess.run(["sudo", "launchctl", "unload", "/Library/LaunchDaemons/com.ollama.plist"], check=True) 
        #subprocess.run(["systemctl", "stop", "ollama"], check=True)
        #print("Ollama service stopped successfully.")

        # Start the Ollama service
        #subprocess.run(["sudo", "launchctl", "load", "/Library/LaunchDaemons/com.ollama.plist"], check=True)
        subprocess.run(["systemctl", "restart", "ollama"], check=True)
        time.sleep(5.0)
        print("Ollama service restarted successfully.")


    except subprocess.CalledProcessError as e:
        print(f"Failed to restart Ollama service: {e}")

    except Exception as e:
        print(f"An error occurred: {e}")
    
def image_to_byte_array(image: Image) -> bytes:
  # BytesIO is a file-like buffer stored in memory
  imgByteArr = BytesIO()
  # image.save expects a file-like as a argument
  image.save(imgByteArr, format=image.format)
  # Turn the BytesIO object back into a bytes object
  imgByteArr = imgByteArr.getvalue()
  return imgByteArr

def get_information_for_image(image_bytes, in_prompt, in_model):
    full_response = ''
    # Generate a description of the image
    for response in ollama.generate(model=in_model, 
                                prompt=in_prompt,
                                images=[image_bytes], 
                                stream=True):
        full_response += response['response']

    return full_response

class Person(BaseModel):
  name: str
  role: str
  #age: int
  #color: str | None
  #favorite_toy: str | None
  
class PersonList(BaseModel):
  person: list[Person]

class RadlDeck:

    def __init__(self, in_deck_checks_location, in_prompt_location):
        self.deck_checks_location = in_deck_checks_location
        self.prompt_location = in_prompt_location

        self.visual_analysis_results = []
        self.report_chapters = {}
        self.report_scores = {}
        self.scientific_hypotheses = ""
        self.company_offering = ""
        self.persons = []

        self.llm_model = "gemma3:12b" #"llama3.2-vision:latest"
        self.report_model = "gemma3:12b" #"phi4:latest" #"phi4-mini:latest" 
        self.score_model = "phi4:latest" #"phi4-mini:latest" 
        self.science_model =  "phi4:latest" #"rohithphoebus/biomistral:latest"

        self.prompt_collection = {}
        # You are an investment analyst at a venture capital company. Analyse this image from a startup's pitch deck and describe all relevant information and interpret the figures. Do not talk about visual style and do not provide a summary or overall impression.
        self.prompt_collection["describe image"] = 'Describe this image and make sure to include anything notable about it (include text you see in the image):'
        self.prompt_collection["classify slide"] = 'Decide for this slide whether it belongs to one of the following categories: problem, solution, product market fit, monetisation, financials, use of funds, organisation, empty page. Please answer just by stating the name of the category.'

        self.prompt_collection["science"] = "You are a medical doctor reviewing a pitchdeck of a health startup. Provide a numbered list of core scientific, health related or medical hypothesis that are addressed by the startup. Do not report market size or any other economic hypotheses. Do not mention the name of the product or the company."
        self.prompt_collection["persons"] = "Provide a list all people in the deck, classify them as staff members, board members, customers, users."
        self.prompt_collection["companies"] = "Provide a list of all companies in the deck, classify them as customers, partners, investors, competitors."
        self.prompt_collection["startup name"] = "State the name of the startup. Make sure to write only the name, not explanation, no introduction."

        self.prompt_collection["role"] = "You are an analyst working at a Venture Capital company. Here is the descriptions of a startup's pitchdeck."
        self.prompt_collection["offering"] = "Your Task is to explain in one single short sentence the service or product the startup provides. Do not mention the name of the product or the company."
        self.prompt_collection["answers"] = "Your task is to find answers to the following questions: "
        self.prompt_collection["scores"] = "Your task is to give a score between 0 and 7 based on how much information is provided for the following questions. Just give a number, no explanations."

        self.prompt_collection["problem"] = 'Who has the problem? What exactly is the nature of the problem? What are the pain points? Can the problem be quantified?'
        self.prompt_collection["solution"] = 'What exactly does your solution look like, what distinguishes it from existing solutions / how does the customer solve the problem so far? Are there competitors and what does their solution & positioning look like? Can you quantify your advantage?'
        self.prompt_collection["product market fit"] = 'Do you have paying customers, do you have non-paying but convinced pilot customers? How did you find them? What do users & payers love about your solution? What is the churn and the reasons for it?'
        self.prompt_collection["monetisation"] = "Who will pay for it? Is it the users of the solution themselves or someone else? What does the buyer's decision-making structure look like, how much time elapses between initial contact and payment? How did you design the pricing and why exactly like this? What are your margins, what are the unit economics?"
        self.prompt_collection["financials"] = 'What is your current monthly burn? What are your monthly sales? Are there any major fluctuations in these two points? If so, why? How much money did you burn last year? How much funding are you looking for, why exactly this amount?'
        self.prompt_collection["use of funds"] = 'What will you do with the money? Is there a ranked list of deficits (not only in the product, but maybe also in the organization or marketing / sales process) that you want to address? Can you tell us about your investment strategy? What will your company look like at the end of this investment period?'
        self.prompt_collection["organisation"] = 'Who are you, what experience do you have, can it be quantified? How can your organizational maturity be described / quantified? How many people are you / pie chart of people per unit? What skills are missing in the management team? What are the most urgent positions that need to be filled?'

        self.do_report = {}
        self.do_report["problem"] = True
        self.do_report["solution"] = True
        self.do_report["product market fit"] = True
        self.do_report["monetisation"] = True
        self.do_report["financials"] = True
        self.do_report["use of funds"] = True
        self.do_report["organisation"] = True

    def get_scientific_hypotheses(self):
        full_pitchdeck_text = " ".join(self.visual_analysis_results)
        self.scientific_hypothesis = ""

        for response in ollama.generate(model=self.science_model, 
                            prompt= self.prompt_collection["science"] +  
                                "Here's the startup's pitchdeck:" + full_pitchdeck_text,
                            stream=True, 
                            options={
                                'num_ctx': 16384
                                }
                            ):
            self.scientific_hypotheses += response['response']

    def get_company_offering(self):
        full_pitchdeck_text = " ".join(self.visual_analysis_results)
        self.company_offering = ""

        model_options = {'num_ctx': 16384}
        for response in ollama.generate(model=self.report_model, 
                                    prompt= self.prompt_collection["role"] + " " +
                                        self.prompt_collection["offering"] +  
                                        " Here is the startup's pitchdeck:" + full_pitchdeck_text,
                                    stream=True, 
                                    options=model_options
                                    ):
            self.company_offering += response['response']

    def get_persons_from_text(self):
        full_pitchdeck_text = " ".join(self.visual_analysis_results)
        # gemma3:12b   
        response = chat(
        messages=[
            {
            'role': 'user',
            'content': full_pitchdeck_text,
            }
        ],
        model='llama3.2',
        format=PersonList.model_json_schema(),
        )

        # pydantic: https://docs.pydantic.dev/latest/concepts/serialization/#modelmodel_dump
        persons_object = PersonList.model_validate_json(response.message.content)
        self.persons = persons_object.model_dump()

    def get_report_data(self, scores_or_answers):
        full_pitchdeck_text = " ".join(self.visual_analysis_results)

        if scores_or_answers == "answers":
            in_model = self.report_model
        else:
            in_model = self.score_model

        for prompt_type, prompt_text in self.prompt_collection.items():

            if prompt_type in self.do_report.keys() and self.do_report[prompt_type] == True:

                if scores_or_answers == "answers":
                    self.report_chapters[prompt_type] = ''
                else:
                    self.report_scores[prompt_type] = ''

                #restart_ollama_service()

                # report per chapter
                # ollama context length is important:
                # https://www.restack.io/p/ollama-api-answer-python-example-cat-ai
                # model_options = {'num_ctx': 16384}
                model_options = {'num_ctx': 32768}
                
                response = ollama.generate(model=in_model, 
                    prompt= self.prompt_collection["role"] + 
                        " " + self.prompt_collection[scores_or_answers] +
                        " questions: " + prompt_text + 
                        " Here is the startup's pitchdeck:" + full_pitchdeck_text,
                    options=model_options
                    )
                if scores_or_answers == "answers":
                    self.report_chapters[prompt_type] = response['response']
                else:
                    self.report_scores[prompt_type] = response['response']


    def save_prompts(self, prompt_name):

        with open(os.path.join(self.prompt_location, prompt_name), 'w', encoding='utf-8') as f:
            out_dic = {}
            out_dic["prompts"] = self.prompt_collection

            out_dic["do_reports"] = self.do_report

            out_dic["llm_model"] = self.llm_model
            out_dic["report_model"] = self.report_model
            out_dic["score_model"] = self.score_model
            out_dic["science_model"] = self.science_model

            json.dump(out_dic, f, ensure_ascii=False, indent=4)

    def load_prompts(self, prompt_name):

        if not(os.path.isfile(os.path.join(self.prompt_location, prompt_name))):
            return False

        with open(os.path.join(self.prompt_location, prompt_name), 'r') as file:
            in_dic = {}
            in_dic = json.load(file)

            if "prompts" in in_dic.keys():
                self.prompt_collection = in_dic["prompts"]
            if "do_reports" in in_dic.keys():
                self.do_report = in_dic["do_reports"]

            if "llm_model" in in_dic.keys():
                self.llm_model = in_dic["llm_model"] 
            if "report_model" in in_dic.keys():
                self.report_model = in_dic["report_model"] 
            if "score_model" in in_dic.keys():
                self.score_model = in_dic["score_model"] 
            if "science_model" in in_dic.keys():
                self.science_model = in_dic["science_model"] 

        return True
    
    def deck_to_json(self):
        out_dic = {}
        out_dic["visual_analysis_results"] = self.visual_analysis_results
        out_dic["report_chapters"] = self.report_chapters
        out_dic["report_scores"] = self.report_scores
        out_dic["scientific_hypotheses"] = self.scientific_hypotheses
        out_dic["company_offering"] = self.company_offering

        return json.dumps(out_dic, ensure_ascii=False, indent=4)        

    def json_to_deck(self, in_json):
        in_dic = {}
        in_dic = json.loads(in_json)

        if "visual_analysis_results" in in_dic.keys():
            self.visual_analysis_results = in_dic["visual_analysis_results"]
        if "report_chapters" in in_dic.keys():
            self.report_chapters = in_dic["report_chapters"]
        if "report_scores" in in_dic.keys():
            self.report_scores = in_dic["report_scores"]
        if "scientific_hypothesis" in in_dic.keys():
            self.scientific_hypothesis = in_dic["scientific_hypothesis"]
        if "company_offering" in in_dic.keys():
            self.company_offering = in_dic["company_offering"]

    def save_deck(self, full_path):
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(self.deck_to_json())

    def load_deck(self, full_path):
        if not(os.path.isfile(full_path)):
            return False

        with open(full_path, 'r') as file:
            loaded_json = file.read()
            self.json_to_deck(loaded_json)

        return True