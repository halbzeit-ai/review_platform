we want to provide feedback to the user, the feedback should be visually
friendly but distinct from other information elements. it will come in a 
form of a comment, i.e. it looks like a piece of chat or discussion thread
below the information element. each feedback will be prefixed by the
"entity" that generated it:

- AI based on analysis of the business case
- GP as humans
- Investors during the funding phase

the startup can react on feedback by:
- replying to the concerns
- adding infomation to the dataroom
- modifying the deck and re-uploading it

our AI needs to give feeback on four levels:
1) feedback on each single deck slide
2) feedback on the template chapters
4) feeback on the slide deck as a whole
1) business case as a whole covering multiple documents


ad 1)
for each slide, we can provide feedback on clarity, visual complexity, and "helpfulness for the biz case"
we need a prompt that looks at the visual analysis of this particular slide and generates feedback on that.


ad 2) 
the templates consist of chapters that cover a single topic during the due dilligence, they
do not follow the structure of the deck but the structure of the GPs thinking how this class of 
startups should be investigated. 

our system already provides feedback on each single question via the scoring functionality.
for the chapters, we introduce a mechanism that looks at the the aggreate for 
- questions plus 
- theirs answers 
- plus their scoring 
meaning that we may have a concatenated context of 4x3 = 12 elements for a chapter that has four
questions and these three elements, or 5x3 = 15 elements if the chapter has five questions and so forth.
we will then use an llm to generate an compact list of maximum five improvements that would enhance this
chapter. 


ad 3)
the deck itself may have weaknesses in story telling, amounts of slides per chapter,
sequence slides in context story telling 
the we render this functionality by looking at the suggestions that we generated in step 2 and then 
generate a suggestion list by taking the set of slides into account. ideally, the system then 
would suggest for example:
- slide 4 needs to go back behind slide 13, 
- here is one slide missing that exmplaings x
- this section has too many slides covering topic y
- the overall number of slides is too high, suggestions for deletions: 6, 12, 18

ad 4)
the business case as a whole should look at the set of documents provided and not just the deck
it should also update, once a document is added to the dataroom, for example a financial report,
a scientific paper or competitor analysis.

in this feedback area, we may have two sections:
- why we recommend to invest
- what is concerning us

