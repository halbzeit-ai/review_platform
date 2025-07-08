* startups can register via email and need to confirm registration via a link in a confirmation email
* they can then upload their pitch deck to the website, the pitch deck is a PDF file
* the PDF file is stored in an S3 bucket that is already hosted on DigitalOcean
* the new upload on S3 triggers a processing as defined in the next bullet point
* an AI python script I already wrote is uploaded to a GPU droplet at DigitalOcean 
* this python script generates a review JSON file that is also stored in the S3 bucket
* we have a postgres database that stores that login data, the link to the deck and link to the review 
* once the review is generated GPs, i.e. human users and owners of the service are contacted via email 
* in that email they will find a link to the review 
* the link will lead them to the website 
* after logging in, they can view the review and make changes
* once they are happy with their changes, they click OK to approve the review
* the startup is then notified via email with a link to the review
* after logging in, the startup will see the review on the website
* the startup can answer any of the GPs' questions in a text field
* when the questions are answered, the GP team is notified again. 
* the questions and answers are also stored in the postgres database and linked to the respective startup

