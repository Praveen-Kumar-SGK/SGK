# import mammoth
# import pdfplumber
# import pdf2docx
# from bs4 import BeautifulSoup
# import pandas as pd
# import os
# import tempfile
# import smbclient
#
# from laserembeddings import Laser
# from sklearn.neural_network import MLPClassifier
# import joblib
#
# from environment import MODE
#
# if MODE == 'local':
#     from .local_constants import *
# else:
#     from .dev_constants import *
#
# document_location = r"/Users/VIJAYKANAGARAJ/PycharmProjects/Schawk_document_xml/Dataset/"
# path_to_bpe_codes = r"/Users/VIJAYKANAGARAJ/PycharmProjects/Schawk_document_xml/Laser/93langs.fcodes"
# path_to_bpe_vocab = r"/Users/VIJAYKANAGARAJ/PycharmProjects/Schawk_document_xml/Laser/93langs.fvocab"
# path_to_encoder = r"/Users/VIJAYKANAGARAJ/PycharmProjects/Schawk_document_xml/Laser/bilstm.93langs.2018-12-26.pt"
#
# #initialize laser
# laser = Laser(path_to_bpe_codes, path_to_bpe_vocab, path_to_encoder)
#
# def albertson_classifier(text):
#     model_location = "".join((document_location,"albertson_model.pkl"))
#     dataset_location = "".join((document_location,"albertson_dataset.xlsx"))
#     if os.path.exists(model_location):
#         classifier = joblib.load(model_location)
#     else:
#         dataframe = pd.read_excel(dataset_location)
#         x_train_laser = laser.embed_sentences(dataframe['text'], lang='en')
#         classifier = MLPClassifier(hidden_layer_sizes=(80,), solver='adam', activation='tanh', max_iter=750, random_state=0,shuffle=True)
#         classifier.fit(x_train_laser, dataframe['category'])
#         joblib.dump(classifier,model_location)
#     prediction = classifier.predict(laser.embed_sentences([text], lang='en'))
#     probability = classifier.predict_proba(laser.embed_sentences([text], lang='en'))
#     probability[0].sort()
#     max_probability = max(probability[0])
#     if max_probability > 0.65:
#         pred_output = prediction[0]
#     else:
#         pred_output = 'None'
#     return {'probability': max_probability, 'output': pred_output}
#
# class Albertson_processing():
#     def __init__(self):
#         self.input_pdf = None
#         self.temp_directory = tempfile.TemporaryDirectory(dir=document_location)
#         self.input_pdf_location = f'{self.temp_directory.name}/input_pdf.pdf'
#
#     def pdf_to_docx_converter(self,page_no):
#         page_no = int(page_no)
#         docx_name = f'{self.temp_directory.name}/{page_no}.docx'
#         if not os.path.exists(docx_name):
#             pdf2docx.parse(self.input_pdf, docx_name, start=page_no - 1, end=page_no)
#         return 'success'
#
#     def docx_to_html_converter(self,docx_name):
#         html = mammoth.convert_to_html(docx_name, style_map="b => b").value
#         return html
#
#     def get_smb_or_local(self,input_pdf):
#         if input_pdf.startswith('\\'):
#             print('connecting to SMB share')
#             try:
#                 with smbclient.open_file(r"{}".format(input_pdf), mode='rb', username=smb_username,password=smb_password) as f:
#                     with open(self.input_pdf_location,'wb') as pdf:
#                         pdf.write(f)
#                 print('file found')
#             except:
#                 raise Exception('File not found')
#             finally:
#                 smbclient.reset_connection_cache()
#             return self.input_pdf_location
#         else:
#             return document_location+input_pdf
#
#     def extraction(self,page_no):
#         docx_converter_status = self.pdf_to_docx_converter(page_no)
#         assert docx_converter_status == 'success', "docx conversion failed"
#         docx_name = f'{self.temp_directory.name}/{page_no}.docx'
#         html = self.docx_to_html_converter(docx_name)
#         soup = BeautifulSoup(html,'html.parser')
#         table = []
#         for row in soup.find_all('tr'):
#             column_values = []
#             for col in row.find_all('td'):
#                 column_values.append(col.text)
#             if len(column_values) >= 2:
#                 table.append(column_values)
#         return table
#
#     def main(self,input_pdf,pages):
#         final_dict = {}
#         self.input_pdf = self.get_smb_or_local(input_pdf)
#         pdf_plumber = pdfplumber.open(self.input_pdf)
#         no_of_pages = len(pdf_plumber.pages)
#         for page in pages.split(','):
#             if int(page)-1 in range(no_of_pages):
#                 try:
#                     data_table = self.extraction(page)
#                     print(data_table)
#                 except:
#                     data_table = [[]]
#                 df = pd.DataFrame(data_table)
#                 rows, columns = df.shape
#                 page_dict = {}
#                 for column in range(columns)[:1]:
#                     for row in range(rows):
#                         header = df[column][row]
#                         classifier_output = albertson_classifier(str(header))
#                         output = classifier_output['output']
#                         if output not in ['None']:
#                             if output in page_dict:
#                                 page_dict[output].append(df[column+1][row])
#                             else:
#                                 page_dict[output] = [df[column + 1][row]]
#                 final_dict[page] = page_dict
#         return final_dict

albertson_output = {"Albertson.pdf": {"1": {'FUNCTIONAL_NAME': [{'es': 'Sous Vide \nEgg Bites\nBacon & 3 Cheese'}],
                           'SUB_BRAND_NAME': [{'en': 'Eggs'}],
                          'VARIANT': [{'en': 'Bacon and Cheese'}],
                          'NET_CONTENT_STATEMENT': [{'sl': 'NET WT 4.6oz (130g)'}],
                          'STORAGE_INSTRUCTIONS': [{'en': 'Perishable | Keep Refrigerated | Fully Cooked'},
                           {'en': 'No'}],
                          'FOOD SAFETY CLASS': [{'en': 'Refrigerated Prepared Foods-Not Ready to Eat (NRTE)'}]},
                    "2":{'WARNING_STATEMENTS': [{'en': 'N/A'}],
                          'IS CALIFORNIA PROP 65 WARNING REQUIRED': [{'en': 'No'}],
                          'DOES PACKAGING CONTAIN BPA': [{'en': 'No'}],
                          'LABEL DISCLOSURES': [{'en': '2 Egg Bites'}],
                          'CONTENT_CLAIM': [{'en': 'Excellent Source of Protein Per Serving'}],
                          'ALLERGEN_STATEMENT': [{'en': 'CONTAINS: EGG, MILK'}]},
                    "3":{'ORGANIC': [{'en': 'No'}],
                          'KOSHER': [{'en': 'No'}],
                          'GLUTEN FREE': [{'en': 'No'}],
                          'FAIR TRADE': [{'en': 'No'}],
                          'NON-GMO': [{'en': 'No'}],
                          'USDA ESTABLISHMENT':[{'en':'Est. 46049'}],
                          'COOKING INSTRUCTIONS':[{'en':'PEEL BACK A CORNER OF FILM TO SLIGHTLY VENT. FOR 1 EGG BITE, MICROWAVE ON HIGH FOR 30 SECONDS. FOR 2 EGG BITES, MICROWAVE ON HIGH FOR 45 SECONDS. LET \nPRODUCT REST FOR 15 SECONDS BEFORE EATING \n(MICROWAVE TIMES MAY VARY)'}],
                          'IS A CAUTION-HOT STATEMENT NEEDED?': [{'en':'YES'}]},
                    "4":{'NUTRITION_FACTS':[{'Fat': [{'Value': {'en':'0.5 g'}},
                           {'PDV': {'en':'1 %'}},
                           {'Value': {'en':'g'}},
                           {'PDV': {'en':'%'}}],
                          'Saturated fatty acids': [{'Value': {'en':'0 g'}},
                           {'PDV': {'en':'0 %'}},
                           {'Value': {'en':'g'}},
                           {'PDV': {'en':'%'}}],
                          'Trans Fat': [{'Value': {'en':'0 g'}}, {'Value': {'en':'g'}}],
                          'Cholestrol': [{'Value': {'en':'0 mg'}},
                           {'PDV': {'en':'0 %'}},
                           {'Value': {'en':'mg'}},
                           {'PDV': {'en':'%'}}],
                          'sodium': [{'Value': {'en':'0 mg'}}, {'PDV': {'en':'0 %'}}, {'Value': {'en':'mg'}}, {'PDV': {'en':'%'}}],
                          'Carbohydrate': [{'Value': {'en':'34 g'}},
                           {'PDV': {'en':'12 %'}},
                           {'Value': {'en':'g'}},
                           {'PDV': {'en':'%'}}],
                          'Dietary Fibre': [{'Value': {'en':'2 g'}},
                           {'PDV': {'en':'7 %'}},
                           {'Value': {'en':'g'}},
                           {'PDV': {'en':'%'}}],
                          'Sugars': [{'Value':{'en':'1 g'}}, {'Value':{'en':'g'}}],
                          'ADDED SUGARS': [{'Value': {'en':'g'}},
                           {'Value': {'en':'0 g'}},
                           {'PDV': {'en':'0 %'}},
                           {'Value': {'en':'g'}},
                           {'PDV': {'en':'%'}}],
                          'Protein': [{'Value': {'en':'6 g'}}, {'Value': {'en':'g'}}],
                          'Vitamin D': [{'Value': {'en':'0 mcg'}},
                           {'PDV': {'en':'0 %'}},
                           {'Value': {'en':'mcg'}},
                           {'PDV': {'en':'%'}}],
                          'calcium': [{'Value': {'en':'0 mg'}},
                           {'PDV': {'en':'0 %'}},
                           {'Value': {'en':'mg'}},
                           {'PDV': {'en':'%'}}],
                          'iron': [{'Value': {'en':'2 mg'}}, {'PDV': {'en':'10 %'}}, {'Value': {'en':'mg'}}, {'PDV': {'en':'%'}}],
                          'potassium': [{'Value': {'en':'70 mg'}},
                           {'PDV': {'en':'2 %'}},
                           {'Value': {'en':'mg'}},
                           {'PDV': {'en':'%'}}],
                           'CALORIES': [{'Value': {'en':'160'}}]
                           }],
                           'Serving Size': [{'en': '1/4 cup (45g)'}]}
                        }}

mondelez_word_output = {'Cloret 182g PLR updated.docx':
    {
            'UNMAPPED':
    	[
    		{'en': 'r'},
    		{'fr': 'Product Label Spec ID No.:  800000052595'},
    		{'de': 'Product Label Spec Report Version No.: 1.0'},
    		{'fr': 'Product Label Spec Status: Approved'},
    		{'en': 'Last Changed By: Oyindamola Oni'},
    		{'de': 'Nigeria - NG\nGhana - GH\n'},
    		{'en': 'Labeling for reformulation or package change'},
    		{'en': '23-NOV-2020'},
    		{'en': '  NG'},
    		{'en': '  GH'},
    		{'en': 'World'},
    		{'en': 'No'},
    		{'en': 'World'},
    		{'en': 'No'},
    		{'en': 'World'},
    		{'en': 'No'},
    		{'en': 'World'},
    		{'en': 'No'},
    		{'en': 'Not Reviewed'},
    		{'en': 'World-6N'},
    		{'en': 'PRODUCTION DATE / LOT / BEST BEFORE: \n'},
    		{'en': 'PRODUCTION DATE / LOT / BEST BEFORE: \n'},
    		{'pt': 'Nutrition Template: WA-PK-Adult (no GDA)\nLabel Set ID No.: 300000009435/003/000'}, {'en': 'Per 100 g'},
    		{'en': '1.Please ensure applying a Space between the number and the unit\n2. Add the international food irradiated symbol, Tidy man symbol, Cadbury trademark.\n3.Please add FOP icon as follow:\nPlease include GDA FOP icon\nPer 2.8 g (2 pieces)\n8.5 Kcal,\n0.43% GDA \n'}
    	],

            'LEGAL_DESIGNATION':
    	[
    		{'en': 'NG: Clorets - Chewing Gum with Sugar and Sweeteners - Original Mint Flavor \n'},
    		{'fr': 'NG: Clorets - Chewing Gum originle avec du sucre et des édulcorants - Saveur Originle Menthe  \n'}
    	],
    		'NET_CONTENT_STATEMENT':
    	[
    		{'en': 'EACH: NG: Net Weight: 2.8 g, 2 Pieces x 1.4 g'},
    		{'en': 'EACH: NG: Poids Net: 2.8 g, 2 Pièces X 1.4 g'}

    	],
            'NUTRITION_FACTS':
    	[
            {'Energy':[{'value':{'en':'1300g'}},{'value':{'en':'2.8g'}}],
            'Calories':[{'value':{'en':'306 kcal'}},{'value':{'en':'8.5kcal'}}],
            'Protein':[{'value':{'en':'0.1 g'}},{'value':{'en':'0 g'}}],
            'Carbohydrate':[{'value':{'en':'76 g'}},{'value':{'en':'2.1 g'}}],
            'of which sugars':[{'value':{'en':'75 g'}},{'value':{'en':'2.1 g'}}],
            'Fat':[{'value':{'en':'0 g'}},{'value':{'en':'0 g'}}],
            'of which saturates':[{'value':{'en':'0 g'}},{'value':{'en':'0 g'}}],
            'Fibre':[{'value':{'en':'0 g'}},{'value':{'en':'0 g'}}],
            'Sodium':[{'value':{'en':'0.01 g'}},{'value':{'en':'0 g'}}]}
    	],
            'NUTRI_DESCRIPTION':
        [
            {'en':'GDA=*The % Daily Value (DV) tells you how much a nutrient in a serving of food contributes to daily diet 2,000 calories a day is used for general nutrition advice'}
        ],
    		'FLAVOR_NAME':
    	[
    		{'en': 'NG: Original Mint Flavour\n'}
    	],
    		'INGREDIENTS_DECLARATION':
    	[
    		{'en': '  \nIngredients: Sugar, Gum Base (Contains Antioxidant - E321), Thickener (Gum Arabic (E414)),\xa0Flavourings\xa0(Mint, Menthol), Glucose Syrup, Starch,\xa0Carrier (E1518)), Sweetener (Aspartame(E951) (0,13 g/100 g) (Non-Nutritive Sweetener)), Vegetable Oils (Fully Hydrogenated Palm Kernel Oil, Non- Hydrogenated Palm Stearin Oil), Colorant (Chlorophyll (E141), Glazing agent (Carnauba Wax (E903)), Emulsifiers from Vegetables source (E433, E471).\n\xa0\n'},
    		{'fr': "  \n \n\nIngrédients: Sucre, Gomme base (avec l'antioxydant E321), Aromatisant (Menthe, Menthol), Agent épaississant (Gomme Arabique (E414)), Sirop de Glucose, Amidon, Solvant de support (Triacétine (1518)), Édulcorants (Aspartame E951(0.13 g/100 g) (Édulcorant Non Nutritifs)), Huile Végétale (Huile de palmiste entièrement hydrogénée, huile de stéarine de palme non hydrogénée), Colorant (Chlorophyll E141), Agent d’enrobage (Cire de Carnauba(E903)), Émulsifiant de Source Végétale (E471, E433).\n\n\xa0\n"}
    	],
    		'ALLERGEN_STATEMENT':
    	[
    		{'en':'\n <b> Contains source of phenylalanine, not to be used by persons who have phenylketonuria. Consult a physician for Pregnant and Lactating women before consumption. </b> This product contains less than the Acceptable Daily Intake: of Aspartame 40mg/ kg of body weight.\n'},
    		{'fr':"\n <b> Contient une source de phénylalanine. Déconseillé auxpersonnes souffrant de laphénylocétonurie. Consulter votre médecin en cas degrossesse ou d’allaitement.  </b> Ce produit contient moins de la dose journaliéreadmissible d'aspartame (40mg/kg de poids corporel).\n\n"}
    	],
    		 'COUNTRY_OF_ORIGIN_STATEMENT':
    	[
    		{'en': 'Made In Egypt\n'}
    	],
	    	'OTHER_INSTRUCTIONS':
    	[
    		{'en': 'NG: Made in Egypt. Manufactured by Mondelez Egypt Foods S.A.E(Formerly Kraft Foods Egypt S.A.E.) (in its branch located at Land 1A and 1B, Block 35, 2nd Industrial Zone, New Borg El Arab City, Alexandria.\nFOR: CADBURY NIGERIA PLC, LATEEF JAKANDE ROAD, AGIDINGBI, IKEJA, LAGOS, NIGERIA.\nFOR: CADBURY GHANA LIMITED, D706/2 HIGH STREET P.O. BOX 49 ACCRA GHANA.\n\n\nWe Care. Hotline\n(In Nigeria):  Toll free line: +2348002232879 (0800 CADBURY)\nEmail: cadbury.nigeria@mdlz.com\nWebsite: www.cadburynigeria.com\n(In Ghana)\nToll free line: +233800200111\nEmail: cadbury.ghana@mdlz.com\n\n\n'},

    		{'fr':'Fabriqué en Egypte\nProduit par Mondelez Egypt Foods S.A.E (anciennement Kraft Foods\nEgypt S.A.E.) á New Borg El Arab, 2nd Industrial Zone, Block 35, Land 1A,\n1B Alexandria. Nous Nous soucion. Numero vert (en Egypte): 16776\nEmail: customercare.mena@mdlz.com\n\n\n\nPOUR: CADBURY NIGERIA PLC, LATEEF JAKANDE ROAD, AGIDINGBI,\nIKEJA, LAGOS, NIGERIA. POUR: CADBURY GHANA LIMITED, D706/2\nHIGH STREET, P.O. BOX 49, ACCRA, GHANA. Marque utilisée sous licence du propriétaire de la marque.\n\n'}
    	],
    		'STORAGE_INSTRUCTIONS':
    	[
    		{'en': 'Store in a cool, dry place. \n'},
    		{'fr': "A conserver à l'abri de la chaleur et de l'humidité. \n"}
    	]
    }
}

mondelez_pdf_output = {'CDM MC-160gx12_PLR.pdf': {
        '1': {
            'UNMAPPED': [{
                'en': 'CADBURY'
                }],
            'FLAVOUR_NAME': [{
                'en': 'MARVELLOUS CREATIONS'
            }],
            'LEGAL_DESIGNATION': [{
                'ar': 'Family Milk Chocolate with fruit flavoured jellies (6%), sugar coated cocoa candies (6%) and popping candy (4%)  \n.)٪٤( ةعقرطملا ىولحلاو )٪٦( ركسلاب ةاطغم واكاكلاب ىولحو )٪٦( هكاوفلا ةهكنب يليجلا ىولحب بيلحلاب )ةيلزنم( ىليماف ةتلاوكوش'
            }],
            'NET_CONTENT_STATEMENT': [{
                'ur': 'Net Weight: 160 g  \nغ ١٦٠ ابيرقت يفاصلا نزولا'
            },{
                'ur': 'Net Weight: 160 g x 12 packs  \nةعطق ١٢ x غ ١٦٠ ابيرقت يفاصلا نزولا'
            }],
            'INGREDIENTS_DECLARATION': [{
                'en': 'Ingredients: Sugar, Full Cream Milk Powder*, Cocoa Mass, Cocoa Butter, Non-Hydrogenated Vegetable Oils (5% Max) (Palm Fruit, Shea Nut), Glucose Syrup, \nInvert Sugar, Lactose (Cow’s Milk), Wheat Starch (Gluten), Emulsifiers From Vegetable Source (E442, E476, E322-Soya), Whey Powder (Cow’s Milk), Reduced \nFat Cocoa Powder, Glazing Agents (Gum Arabic, Beeswax, Carnauba Wax), Colourants (E101, E160a, E162, E163, E171, E172), Natural And Artificial Flavorings \n(Cherry, Butter, Vanillin), Acid (E330). \nFamily Milk Chocolate: Milk Solids 20% Min. Cocoa Solids 20% Min.  \nContains Vegetable Fats In Addition To Cocoa Butter. \n*Full Cream Milk Powder Is Equivalent Of Glass And A Half Milk In Every 200 g Of Cadbury Dairy Milk Chocolate. \n \nCONTAINS: COW’S MILK, SOYA, WHEAT (GLUTEN). \nMAY CONTAIN: TREE NUTS.'
            }, {
                'ar': '،)يرقب بيلح( زوتكلا ،لوحم ركس ،زوكولجلا بارش ،)ايش تيز ،)ةهكاف نم جرختسم( ليخن تيز( )٪٥ نع ديزت لا( ةجردهم ريغ ةيتابن تويز ،واكاك ةدبز ،واكاك ةلتك ،*مسدلا لماك بيلح قوحسم ،ركس :تانوكملا\n ،)ابونراكلا عمش ،لحنلا عمش ،يبرع غمص( عيملت داوم ،مسدلا ضفخنم واكاك قوحسم ، )يرقب بيلح( بيلح لصم قوحسم ، )ايوص -٣٢٢ يإ ،٤٧٦ يإ ،٤٤٢ يإ( يتابن ردصم نم تابلحتسم ، )نيتولج( حمقلا اشن\n.)٣٣٠ يإ( ضماح ، )نيليناف ،ةدبز ،زيرك( ةيعيبط و ةيعانص تاهكن ، )١٧٢ يإ ،١٧١ يإ ،١٦٣ يإ ،١٦٢ يإ ،أ١٦٠ يإ ،١٠١ يإ( ناولأ \n .واكاكلا ةدبز ىلإ ةفاضلإاب ةيتابن نوهد ىلع يوتحت .ىندا دحك ٪٢٠:واكاكلا دماوج .ىندأ دحك ٪٢٠ :بيلحلا دماوج :بيلحلاب )ةيلزنم( يليماف ةتلاوكوش'
            }],
       'ALLERGEN_STATEMENT': [{
                'en': '<b>Contains Vegetable Fats In Addition To Cocoa Butter. \n*Full Cream Milk Powder Is Equivalent Of Glass And A Half Milk In Every 200 g Of Cadbury Dairy Milk Chocolate. \n \nCONTAINS: COW’S MILK, SOYA, WHEAT (GLUTEN). \nMAY CONTAIN: TREE NUTS.</b>'
            }, {
                'ar': '<b>،٠ .واكاكلا ةدبز ىلإ ةفاضلإاب ةيتابن نوهد ىلع يوتحت .ىندا دحك ٪٢٠:واكاكلا دماوج .ىندأ دحك ٪٢٠ :بيلحلا دماوج :بيلحلاب )ةيلزنم( يليماف ةتلاوكوش</b>'}]
        },
        '2': {

            'UNMAPPED': [{

                'en': 'World'

            }, {

                'en': 'No'

            }, {

                'en': 'World'

            }, {

                'en': 'No'

            }, {

                'en': 'World'

            }, {

                'en': 'No'

            }, {

                'en': 'Not Reviewed'

            }, {

                'ar': 'ناضمر نم شراعلا ةنيدم –  ٢ب  ةيناثلا ةيعانصلا ةقطنملا فيز نئاكلا عرفلا فيز م.م.ش زدوف تبيجيإ يز ليدنوم جاتنإ .صرم فيز عنص'

            }, {

                'en': 'World-6N'

            }, {

                'en': 'PRODUCTION DATE / LOT / BEST BEFORE:'

            }],

            'OTHER_INSTRUCTIONS': [{

                'en': 'Made in Egypt. Manufactured by Mondelez Egypt Foods S.A.E.in its branch located at Second Industrial Zone B2, \nTenth of Ramadan.'

            }, {

                'ar': '١٦٧٧٦ صرم لخاد نخاسلا طخلا لىع ا نب لصتا انمهي مكيأر \nWe care. Call us (hotline) in Egypt 16776. \nز ر\nEmail: customercare.mena@mdlz.com  : ني ويكللإا دييرلا \nز ر\nWeb: www.mondelezinternational.com  : نويكللإا عقوملا \nي'

            }],

            'LOCATION_OF_ORIGIN': [{

                'ar': 'Made in Egypt \nرصم يف عنص'

            }]

        },

        '3': {

            'UNMAPPED': [{

                'en': ''

            }, {

                'en': 'World-AR'

            }, {

                'ar': 'لبق هكلاهتسا لضفي/ةليغشتلا مقر/جاتنلاا خيرات'

            }, {

                'ar': 'ةرشابملا سمشلا ةعشا نع اديعب فاج و دراب ناكم ىف ظفحت'

            }, {

                'en': '8'

            }],

            'STORAGE_INSTRUCTIONS': [{

                'en': 'Keep in a cool & dry place away from direct sunlight'

            }],

               },

        '4':{ 'NUTRITION_FACTS':

    [

            {

             'Energy':[{'VALUE':{'en':'1300g'}},{'VALUE':{'en':'2.8g'}}],

            'Calories':[{'VALUE':{'en':'306 kcal'}},{'VALUE':{'en':'8.5kcal'}}],

            'Protein':[{'VALUE':{'en':'0.1 g'}},{'VALUE':{'en':'0 g'}}],

            'Carbohydrate':[{'VALUE':{'en':'76 g'}},{'VALUE':{'en':'2.1 g'}}],

            'of which sugars':[{'VALUE':{'en':'75 g'}},{'VALUE':{'en':'2.1 g'}}],

            'Fat':[{'VALUE':{'en':'0 g'}},{'VALUE':{'en':'0 g'}}],

            'of which saturates':[{'VALUE':{'en':'0 g'}},{'VALUE':{'en':'0 g'}}],

            'Fibre':[{'VALUE':{'en':'0 g'}},{'VALUE':{'en':'0 g'}}],

            'Sodium':[{'VALUE':{'en':'0.01 g'}},{'VALUE':{'en':'0 g'}}]

             }

    ]

},

    '5': {}

}}








