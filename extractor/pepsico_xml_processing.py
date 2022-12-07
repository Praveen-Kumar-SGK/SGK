from bs4 import BeautifulSoup
import tempfile

from .excel_processing import *

from environment import MODE

if MODE == 'local':
    from .local_constants import *
else:
    from .dev_constants import *

# input_xml = r"/Users/vijaykanagaraj/PycharmProjects/pepsico/104475697_402080858/160220077_20201024_17-48-30.xml"

mapping_dict = {'fopproductdescriptor': 'FUNCTIONAL_NAME',
 'bopproductdescriptor': 'FUNCTIONAL_NAME',
 'ingredientsdeclaration': 'INGREDIENTS_DECLARATION',
 'servingstatement': 'SERVING_SIZE',
 'referenceintakestatement': 'REFERENCE_INTAKE_STATEMENT',
 'storagestatement': 'STORAGE_INSTRUCTIONS',
 'bestbefore': 'BEST_BEFORE_DATE',
 'customercarestatement': 'CONSUMER_GUARANTEE',
 'customercarestatementaddress': 'CONTACT_INFORMATION',
 'webaddress': 'WEBSITE',
 'packclaims': 'MARKETING_CLAIM',
 'ingredientsclaims': 'MARKETING_CLAIM',
 'nutritionalclaims': 'NUTRITIONAL_CLAIM',
 'distributoraddress': 'CONTACT_INFORMATION',
 'allergenadvicetitle':'ALLERGEN_STATEMENT',
 'madefactory':'ALLERGEN_STATEMENT',
 'contains':'DISCLAIMER',
 'brand':'BRAND_NAME',
 'subbrand':'SUB_BRAND_NAME',
 'protectiveenvironmentstatement':'ENVIRONMENT_STATEMENTS',
                }


def html_clean(text):
    print(text)
    print('-------'*10)
    replace_dict = {}
    soup = BeautifulSoup(str(text), "html.parser")
    for t in soup.find_all():
        # if not t.parent.name == "span":
        print("vaaaaadi------->",t.name)
        if not t.parent.name == "[Document]" and t.name == "span":
            if "bold" in str(t) and str(t.text).strip():
                print('inside single span')
                clean_text = t.text
                print(clean_text)
                if clean_text:
                    to_replace_text = f"<b>{clean_text}</b>"
                    replace_dict[str(t)] = to_replace_text
            elif not str(t.text).strip():
                replace_dict[str(t)] = ""
    for key, value in replace_dict.items():
        print("key--------->",key)
        print("value--------->",value)
        try:
            text = re.sub(r"{}".format(key),value,text)
        except:
            text = text.replace(key,value)
    text = text.replace(']]&gt;', '').strip()
    text = re.sub(r"^n\/?a$","",text,flags=re.I)
    text = re.sub(r"<\/?(br).*?>","",text)
    text = re.sub(r"<(?!\/?b).*?>", "", text).strip()
    text = text.replace(">","&gt;").replace("<","&lt;")
    return text

def get_input(file,input_location):
    if file.startswith('\\'):
        print('connecting to SMB share')
        try:
            with smbclient.open_file(r"{}".format(file), mode='rb', username=smb_username,
                                     password=smb_password) as f:
                with open(input_location,'wb') as input:
                    input.write(f.read())
                print('file found')
        except:
            smbclient.reset_connection_cache()
            with smbclient.open_file(r"{}".format(file), mode='rb', username=smb_username,
                                     password=smb_password) as f:
                with open(input_location,'wb') as input:
                    input.write(f.read())
                print('file found')
        finally:
            smbclient.reset_connection_cache()
        return input_location
    else:
        return document_location+file

def xml_processing(file_input):
    temp_dict = {}
    temp_directory = tempfile.TemporaryDirectory(dir=document_location)
    input_xml_location = f'{temp_directory.name}/input.xml'
    input_xml = get_input(file_input,input_xml_location)
    with open(input_xml,"r") as xml:
        soup = BeautifulSoup(xml,"lxml")
        for copy in soup.find_all('copy'):
            for copyelement in copy.find_all('copyelement'):
                for content in copyelement.find_all(re.compile(r"^(?!p|span|b|strong)")):
                    try:
                        cate = mapping_dict[copyelement.attrs['category'].lower()]
                    except:
                        cate = "unmapped"
                    content = html_clean(str(content))
                    if content:
                        try:
                            lang = lang_detect(content)
                        except:
                            lang = classify(content)[0]
                        if cate in temp_dict:
                            temp_dict[cate].append({lang:content})
                        else:
                            temp_dict[cate] = [{lang:content}]
        for tag in soup.find_all(['brand','subbrand']):
            try:
                cate = mapping_dict[tag.name]
            except:
                cate = tag.name
            if tag.text.strip():
                try:
                    lang = lang_detect(content)
                except:
                    lang = classify(content)[0]
                if cate in temp_dict:
                    temp_dict[cate].append({lang:tag.text})
                else:
                    temp_dict[cate] = [{lang:tag.text}]
    return temp_dict


# xx = xml_processing(input_xml)

# print(xx)

# x = {'FUNCTIONAL_NAME': [{'en': 'PopWorks Pop Corn Crisps Sea Salt'}, {'en': 'PopWorks Pop Corn Crisps Sea Salt'}, {'en': 'N/A'}, {'en': 'N/A'}, {'en': 'Sea Salted Corn Crisps'}, {'en': 'Sea Salted Corn Crisps'}, {'fr': 'Chips de maïs au sel de mer'}, {'nl': 'Maïschips met zeezout'}], 'INGREDIENTS_DECLARATION': [{'de': '&lt;b&gt;Ingredients:&lt;/b&gt; Corn (90%), Sunflower Oil, Sea Salt.'}, {'de': '&lt;b&gt;Ingredients:&lt;/b&gt; Corn (90%), Sunflower Oil, Sea Salt.'}, {'fr': 'maïs (90%), huile de tournesol, sel de mer'}, {'nl': 'Ingrediënten: maïs (90%), zonnebloemolie, zeezout.'}], 'SERVING_SIZE': [{'en': 'This pack contains 1 serving'}, {'en': 'This pack contains 1 serving'}, {'fr': 'Cet emballage contient une portion.'}, {'nl': 'Deze verpakking bevat 1 portie.'}], 'REFERENCE_INTAKE_STATEMENT': [{'en': '* Reference intake of an average adult (8400 kJ/2000 kcal)'}, {'en': '* Reference intake of an average adult (8400 kJ/2000 kcal)'}, {'fr': '* Apport de référence pour un adulte-type (8400 kJ / 2000 kcal)'}, {'nl': '* Referentie inname van een gemiddelde volwassene (8400kJ / 2000kcal)'}], 'STORAGE_INSTRUCTIONS': [{'en': 'Store in cool, dry place.'}, {'en': 'Store in cool, dry place.'}, {'fr': 'Conserver au sec.'}, {'nl': 'Koel en droog bewaren.'}], 'BEST_BEFORE_DATE': [{'en': 'Best Before'}, {'en': 'Best Before'}, {'fr': 'A consommer de préférence avant le'}, {'nl': 'Ten minste houdbaar tot'}], 'CONSUMER_GUARANTEE': [{'en': 'If dissatisfied, tell us why by contacting us on:'}, {'en': 'If dissatisfied, tell us why by contacting us on:'}, {'fr': 'Vous n’êtes pas satisfait de nos chips ? Envoyez-nous votre emballage avec son contenu, vos remarques et vos coordonnées. Indiquez également où et quand vous avez acheté nos chips. Inutile d’affranchir! (en Belgique uniquement).'}, {'nl': 'Ben je niet tevreden over onze chips? Stuur ons je opmerkingen, verpakking met de inhoud en contactgegevens. Vermeld even waar en wanneer je onze chips hebt gekocht. Postzegels? Niet nodig!'}, {'en': 'Please have product available when contacting us. Your statutory rights are not affected.'}, {'en': 'Please have product available when contacting us. Your statutory rights are not affected.'}, {'en': 'N/A'}, {'en': 'N/A'}], 'CONTACT_INFORMATION': [{'de': 'www.popworks-snacks.com'}, {'de': 'www.popworks-snacks.com'}, {'en': 'NA'}, {'en': 'N/A'}, {'en': 'PopWorks Consumer Care, PO Box 23, Leicester, LE4 8ZU, UK. 0800 274 777 (Freephone) Lines open Weekdays 9am-5pm'}, {'en': 'PopWorks Consumer Care, PO Box 23, Leicester, LE4 8ZU, UK. 0800 274 777 (Freephone) Lines open Weekdays 9am-5pm'}, {'fr': 'Antwoordcode / Code-Réponse DA 852-219-5, Consumenten Service Consommateurs - BE, 1930 Zaventem, België.'}, {'nl': 'Consumentenservice, Antwoordnummer 2460, 3600 VB Maarssen, Nederland.'}, {'en': 'N/A for UK'}, {'en': 'N/A for UK'}, {'en': 'N/A'}, {'en': 'PepsiCo Nederland BV, zonnebaan 35, 3542 EB, Utrecht, the Netherlands.'}], 'WEBSITE': [{'en': 'POPWORKS-SNACKS.COM'}, {'en': 'POPWORKS-SNACKS.COM'}, {'en': 'NA'}, {'en': 'N/A'}, {'en': '@POPWORKSSNACKS'}, {'en': '@POPWORKSSNACKS'}, {'en': 'NA'}, {'en': 'N/A'}], 'Disclaimer': [{'sv': 'May Contain: Soya, Milk.'}, {'sv': 'May Contain: Soya, Milk.'}, {'fr': 'Peut contenir des traces de soja et lait.'}, {'nl': 'Kan sporen van soja en melk bevatten.'}, {'en': 'Not suitable for milk allergy sufferers'}, {'en': 'Not suitable for milk allergy sufferers'}, {'fr': 'Ne convient pas aux personnes allergiques au lait'}, {'nl': 'Niet geschikt voor mensen met melkallergie'}], 'MARKETING_CLAIM': [{'en': 'Vegan'}, {'en': 'Vegan'}, {'fr': 'Végétalien'}, {'de': 'Veganistisch'}, {'de': 'Gluten free'}, {'de': 'Gluten free'}, {'fr': 'Sans gluten'}, {'hr': 'Glutenvrij'}, {'da': 'Never fried'}, {'da': 'Never fried'}, {'fr': 'Sans friture'}, {'da': 'Zonder frituren'}, {'en': '&amp;amp; No Artificial Flavours, Colours or Preservatives'}, {'en': '&amp;amp; No Artificial Flavours, Colours or Preservatives'}, {'fr': '&amp;amp; Sans arômes, colorants ou conservateurs artificiels'}, {'nl': '&amp;amp; Geen kunstmatige smaakstoffen, kleurstoffen of conserveringsmiddelen'}, {'en': 'Only 3 ingredients'}, {'en': 'Only 3 ingredients'}, {'fr': 'Seulement 3 ingrédients'}, {'nl': 'Slechts 3 ingrediënten'}], 'BRAND_NAME': [{'en': 'PopWorks'}], 'SUB_BRAND_NAME': [{'en': 'Pop Corn'}]}
# response = {"file.xml":{'FUNCTIONAL_NAME': [{'en': 'PopWorks Pop Corn Crisps Sea Salt'}, {'en': 'PopWorks Pop Corn Crisps Sea Salt'}, {'en': 'N/A'}, {'en': 'N/A'}, {'en': 'Sea Salted Corn Crisps'}, {'en': 'Sea Salted Corn Crisps'}, {'fr': 'Chips de maïs au sel de mer'}, {'nl': 'Maïschips met zeezout'}], 'INGREDIENTS_DECLARATION': [{'de': '&lt;b&gt;Ingredients:&lt;/b&gt; Corn (90%), Sunflower Oil, Sea Salt.'}, {'de': '&lt;b&gt;Ingredients:&lt;/b&gt; Corn (90%), Sunflower Oil, Sea Salt.'}, {'fr': 'maïs (90%), huile de tournesol, sel de mer'}, {'nl': 'Ingrediënten: maïs (90%), zonnebloemolie, zeezout.'}], 'SERVING_SIZE': [{'en': 'This pack contains 1 serving'}, {'en': 'This pack contains 1 serving'}, {'fr': 'Cet emballage contient une portion.'}, {'nl': 'Deze verpakking bevat 1 portie.'}], 'REFERENCE_INTAKE_STATEMENT': [{'en': '* Reference intake of an average adult (8400 kJ/2000 kcal)'}, {'en': '* Reference intake of an average adult (8400 kJ/2000 kcal)'}, {'fr': '* Apport de référence pour un adulte-type (8400 kJ / 2000 kcal)'}, {'nl': '* Referentie inname van een gemiddelde volwassene (8400kJ / 2000kcal)'}], 'STORAGE_INSTRUCTIONS': [{'en': 'Store in cool, dry place.'}, {'en': 'Store in cool, dry place.'}, {'fr': 'Conserver au sec.'}, {'nl': 'Koel en droog bewaren.'}], 'BEST_BEFORE_DATE': [{'en': 'Best Before'}, {'en': 'Best Before'}, {'fr': 'A consommer de préférence avant le'}, {'nl': 'Ten minste houdbaar tot'}], 'CONSUMER_GUARANTEE': [{'en': 'If dissatisfied, tell us why by contacting us on:'}, {'en': 'If dissatisfied, tell us why by contacting us on:'}, {'fr': 'Vous n’êtes pas satisfait de nos chips ? Envoyez-nous votre emballage avec son contenu, vos remarques et vos coordonnées. Indiquez également où et quand vous avez acheté nos chips. Inutile d’affranchir! (en Belgique uniquement).'}, {'nl': 'Ben je niet tevreden over onze chips? Stuur ons je opmerkingen, verpakking met de inhoud en contactgegevens. Vermeld even waar en wanneer je onze chips hebt gekocht. Postzegels? Niet nodig!'}, {'en': 'Please have product available when contacting us. Your statutory rights are not affected.'}, {'en': 'Please have product available when contacting us. Your statutory rights are not affected.'}, {'en': 'N/A'}, {'en': 'N/A'}], 'CONTACT_INFORMATION': [{'de': 'www.popworks-snacks.com'}, {'de': 'www.popworks-snacks.com'}, {'en': 'NA'}, {'en': 'N/A'}, {'en': 'PopWorks Consumer Care, PO Box 23, Leicester, LE4 8ZU, UK. 0800 274 777 (Freephone) Lines open Weekdays 9am-5pm'}, {'en': 'PopWorks Consumer Care, PO Box 23, Leicester, LE4 8ZU, UK. 0800 274 777 (Freephone) Lines open Weekdays 9am-5pm'}, {'fr': 'Antwoordcode / Code-Réponse DA 852-219-5, Consumenten Service Consommateurs - BE, 1930 Zaventem, België.'}, {'nl': 'Consumentenservice, Antwoordnummer 2460, 3600 VB Maarssen, Nederland.'}, {'en': 'N/A for UK'}, {'en': 'N/A for UK'}, {'en': 'N/A'}, {'en': 'PepsiCo Nederland BV, zonnebaan 35, 3542 EB, Utrecht, the Netherlands.'}], 'WEBSITE': [{'en': 'POPWORKS-SNACKS.COM'}, {'en': 'POPWORKS-SNACKS.COM'}, {'en': 'NA'}, {'en': 'N/A'}, {'en': '@POPWORKSSNACKS'}, {'en': '@POPWORKSSNACKS'}, {'en': 'NA'}, {'en': 'N/A'}], 'Disclaimer': [{'sv': 'May Contain: Soya, Milk.'}, {'sv': 'May Contain: Soya, Milk.'}, {'fr': 'Peut contenir des traces de soja et lait.'}, {'nl': 'Kan sporen van soja en melk bevatten.'}, {'en': 'Not suitable for milk allergy sufferers'}, {'en': 'Not suitable for milk allergy sufferers'}, {'fr': 'Ne convient pas aux personnes allergiques au lait'}, {'nl': 'Niet geschikt voor mensen met melkallergie'}], 'MARKETING_CLAIM': [{'en': 'Vegan'}, {'en': 'Vegan'}, {'fr': 'Végétalien'}, {'de': 'Veganistisch'}, {'de': 'Gluten free'}, {'de': 'Gluten free'}, {'fr': 'Sans gluten'}, {'hr': 'Glutenvrij'}, {'da': 'Never fried'}, {'da': 'Never fried'}, {'fr': 'Sans friture'}, {'da': 'Zonder frituren'}, {'en': '&amp;amp; No Artificial Flavours, Colours or Preservatives'}, {'en': '&amp;amp; No Artificial Flavours, Colours or Preservatives'}, {'fr': '&amp;amp; Sans arômes, colorants ou conservateurs artificiels'}, {'nl': '&amp;amp; Geen kunstmatige smaakstoffen, kleurstoffen of conserveringsmiddelen'}, {'en': 'Only 3 ingredients'}, {'en': 'Only 3 ingredients'}, {'fr': 'Seulement 3 ingrédients'}, {'nl': 'Slechts 3 ingrediënten'}], 'BRAND_NAME': [{'en': 'PopWorks'}], 'SUB_BRAND_NAME': [{'en': 'Pop Corn'}]}}