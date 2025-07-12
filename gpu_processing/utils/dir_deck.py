import glob
import os
import time
#from tqdm import tqdm
import boto3
import io

from pdf2image import convert_from_path, convert_from_bytes
from checker_radl import radlchecker

from uuid import uuid4
import getopt, sys


tokenizer_name = "sentence-transformers/all-MiniLM-L12-v2"
embeddings_name = "sentence-transformers/all-mpnet-base-v2"
prompt_location = "../data/prompts"
prompt_name = "decks.json"

single_file = False
cloud_data = "local" # "cloud" #
max_decks = -1

# Remove 1st argument from the
# list of command line arguments
argumentList = sys.argv[1:]

# Options
options = "l:f:m:"

try:
    # Parsing argument
    arguments, values = getopt.getopt(argumentList, options)
    
    # checking each argument
    for currentArgument, currentValue in arguments:
        print(f"'{currentArgument}': '{currentValue}'")

        if currentArgument == "-l":
            if (currentValue == "cloud") or (currentValue == "local"):
                cloud_data = currentValue
            else:
                raise Exception(f"invalid arg {currentValue}, valid args for location: cloud or local")
                
        elif currentArgument == "-f":
            single_file = True
            if currentValue.endswith(".pdf"):
                single_file_name = currentValue
            else:
                raise Exception("file must be a pdf")
            
        elif currentArgument == "-m":
            max_decks = currentValue
            
except getopt.error as err:
    # output error, and return with an error code
    print (str(err))

print("computing")
all_deck_files = []
if cloud_data == "cloud":
    # paths
    cloud_pdfs = "pitchdecks"
    cloud_jsons = "analyses"

    # DigitalOcean Spaces credentials - load from environment
    SPACES_ACCESS_KEY = os.getenv("DO_SPACES_KEY")
    SPACES_SECRET_KEY = os.getenv("DO_SPACES_SECRET")
    
    if not SPACES_ACCESS_KEY or not SPACES_SECRET_KEY:
        print("Warning: DigitalOcean Spaces credentials not configured. Cloud storage disabled.")
        cloud_data = "local"  # Force local mode if no credentials
    SPACES_BUCKET = "nector-reloaded"
    SPACES_REGION = "fra1"
    SPACES_ENDPOINT = "https://nector-reloaded.fra1.digitaloceanspaces.com"

    # Initialize DigitalOcean Spaces client
    session = boto3.session.Session()
    s3_client = session.client(
        's3',
        region_name=SPACES_REGION,
        endpoint_url="https://fra1.digitaloceanspaces.com",
        aws_access_key_id=SPACES_ACCESS_KEY,
        aws_secret_access_key=SPACES_SECRET_KEY
    )

    #https://dev.to/aws-builders/how-to-list-contents-of-s3-bucket-using-boto3-python-47mm
    objects = s3_client.list_objects_v2(Bucket=SPACES_BUCKET)

    if single_file == False:
        for obj in objects['Contents']:
            cloud_path = obj['Key']
            if cloud_path.startswith(cloud_pdfs) and cloud_path.endswith(".pdf"):
                all_deck_files.append(cloud_path)
                print(cloud_path)
    else:
        all_deck_files.append(cloud_pdfs + "/" + single_file_name)

else:
    # paths
    local_pdfs = "../data/pdf/pitchdecks"
    local_jsons = "../data/deck_checks"

    if single_file == False:
        all_deck_files = glob.glob(os.path.join(local_pdfs, "*.pdf"))
    else:   
        all_deck_files.append(local_pdfs + "/" + single_file_name)


def save_deck_json(in_deck, in_full_path):
    in_pdf_name = in_full_path.split("/")[-1]
    json_filename = in_pdf_name.split(".")[0] + ".json"
    sub_dir = in_full_path.split("/")[-2]

    if cloud_data == "local":
        json_file_incl_path = f"{local_jsons}/{sub_dir}/{json_filename}"
        print(f"save local json: {json_file_incl_path}")
        in_deck.save_deck(json_file_incl_path)
    else:
        json_file_incl_path = f"{cloud_jsons}/{sub_dir}/{json_filename}"
        print(f"save cloud json: {json_file_incl_path}")
        json_object = in_deck.deck_to_json()
        s3_client.put_object(Body=json_object, Bucket=SPACES_BUCKET, Key=json_file_incl_path)

def process_all_decks(all_deck_files):
    
    no_of_decks = len(all_deck_files)
    deck_counter = 1
    documents = []
    broken_files = []
    for single_deck in all_deck_files:
        start_time = time.time()

        print(f"analysing deck {deck_counter} of {no_of_decks}")
        try:
            current_deck = radlchecker.RadlDeck(single_deck, prompt_location)

            #current_deck.llm_model = "llama3.2-vision:latest"
            
            if cloud_data == "cloud":
                pdf_name = single_deck.split("/")[-1]

                pdf_buffer = io.BytesIO()
                s3_client.download_fileobj(SPACES_BUCKET, single_deck, pdf_buffer)
                pdf_buffer.seek(0)

                pages_as_images = convert_from_bytes(pdf_buffer.read(), fmt="jpeg")
            else:
                doc_path, pdf_name = os.path.split(single_deck)
                pages_as_images = convert_from_path(single_deck, fmt="jpeg")

            max_pages = len(pages_as_images)-1
            
            # this is from process_document():
            #for page_number in tqdm(range(max_pages)):
            for page_number in range(max_pages):

                single_page_as_image = pages_as_images[page_number]
                image_bytes = radlchecker.image_to_byte_array(single_page_as_image)
                page_vision_analysis = radlchecker.get_information_for_image(image_bytes, current_deck.prompt_collection["describe image"], current_deck.llm_model)

                current_deck.visual_analysis_results.append(page_vision_analysis)

            current_deck.get_company_offering()
            current_deck.get_report_data("answers")
            current_deck.get_report_data("scores")
            current_deck.get_scientific_hypotheses()

            save_deck_json(current_deck, single_deck)

            end_time = time.time()        
            print(f"{pdf_name}: pages: {max_pages}, processing time: {int((end_time-start_time)/60)}min.")

            if max_decks > 0:
                if deck_counter == max_decks: 
                    break

            deck_counter+=1
        except Exception as deck_ex:
            broken_files.append(single_deck)
            print(f"error processing deck {single_deck}: {deck_ex}")
    
    print("broken files:")
    print("\n".join(broken_files))

process_all_decks(all_deck_files)
