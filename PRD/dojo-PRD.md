Idea behind the dojo part of the system:
the goal of the dojo processing is that a GP can view a processing result as if they are a startup 
and to see what the startup for this deck would experience. 
when changing a prompt or a model, the GP would see that the texts are shorter, have a different quality or the scoring changes.

the idea is that the GP is "impersonating" a startup and can use all of the ui and workflows that a startup has, 
not only the results viewer but really the whole project. 
in the future, we will have more document types than only pitchdecks, for example financial reports and research papers. 
so we need to be able to view all of these like a startup does.

- This part is intended for GPs to work on a large number of decks to improve prompts.
- for this, the GP can upload zip files and will then have a lot of pdf files. this is done in the "training data & management" tab of dojo
- step 1: next the GP can generate a random sub-sample of the PDF pool
- steps 2, 3 and 4 run on the GPU and it communicates with the CPU server via HTTP, the CPU has a postgresql database where all info about PDFs and results is stored-
- step 2: subsequent steps work on text only. step 2 turns the pdf into single images and interprets these images,  turning them into text descriptions per page.
- as step 2 takes quite a while, we have introduced caching so that the translation from images to text is stored in the database on the CPU.
- the user may clear the cache to do the visual analysis of step 2 again, maybe with a better and slower LLM
- step 2 should and must do exactly only this. get an image interpretation prompt and the selected model from the database and generate visual results to be stored in the database
- step 3 extracts via multiple prompts and possibly different LLM the following informations from the deck: the company's offering, the class, the name of the company, the funding amount and the date of the deck. these are obligatory and need to be extracted for every deck as they do not relate to the sub-vertical / class the startup is in.
- step 4 finally, gets a template (one that the user selected) from the database, this template consists roughly of a couple of chapters, each chapter has a couple questions and a corresponding scoring criterion.
- step 4 generates a results report that has the identical structure as the results.json that is generated when startups upload their deck via the web upload mechanism. this structure is stored in the database.
- finally, the user can look at the some key information of such an experimental run in the extraction experiment history: company name, number of pages in the deck, class, offering.
- here, the user can add these companies as fake companies to the startup database and look at these dojo companies through the eyes of a startup founder.
- the dojo companies can be accessed via the GP dashboard in the gallery, that shows the fist image of the deck, company name, funding sought and company offering, i.e. mostly information from step 3.
- clicking on "open project" of a dojo company will show the startup view on a project.
- here, the GP can click on the deck viewer that will view the visual analysis from step 2 together with the images extracted from the deck.
- the GP can also open the results viewer to see all results from step 4.
- finally, the GP can remove the experimental dojo companies again in the "training data & management" tab of dojo

here's another description from the discussion with claude code:
- dojo is built in a way that selecting a sample generates a new experiment. 
- when one or more processing steps are done, the user can to the experiments history tab, 
- there, he can select an exeriment leading him to the experiment results. 
- the experiment results are a modal that shows each company of the sample incl company name, class, funding sought and the offering. 
- this is very handy to understand whether the obligatory extractions work. 
- if the user likes the results of the experiment overview, he can click "add dojo companies" on the right lower side. 
- this function will add the companies of this experiment as projects to the gallery view. 
- thus, dojo is not automatically populating the gallery, the user is in control and will only do so when the table of experiment results is satisfactory. 
- in the GP dashboard, you see the piechart that shows the distribution of the companies in the project database. 
- there, the user can select whether to see dojo companies ("include test data", we should rename that to "include dojo companies"). 
- if this is done, the gallery view will show legit startups as well as dojo companies. 
- finally, when the user is done with this dojo sample and companies, he can remove all the dojo companies by going to the dojo ui, navigating to "training  data & management" and hitting "clean up dojo projects"
- this will remove the dojo companies from the project database. 
