import xml.etree.ElementTree as ET
import re
import argparse
import sqlite3

MW_NS = '{http://www.mediawiki.org/xml/export-0.10/}'
SILL_TPL = "{{-sill-}}"

parser = argparse.ArgumentParser()
parser.add_argument('-f', '--filename', type=str, required=False, default='itwiktionary-latest-pages-meta-current.xml')
parser.add_argument('-a', '--accenti', required=False, action='store_true')
parser.add_argument('-l', '--link', required=False, action='store_true')
parser.add_argument('-s', '--sql', required=False, action='store_true')
parser.add_argument('-d', '--db', type=str, required=False, default='wiki.sqlite3')
parser.add_argument('-t', '--table', type=str, required=False, default='itwiktionary')
args = parser.parse_args()

xml_wikidump_file = args.filename

if args.sql:
    con = sqlite3.connect(args.db)
    cur = con.cursor()
    cur.execute("DROP TABLE IF EXISTS " + args.table +  ";")
    cur.execute('CREATE TABLE "' + args.table +  '" ("lemma" TEXT NOT NULL, "link" TEXT, "sillabazione" TEXT )')


tree = ET.parse(xml_wikidump_file)
root = tree.getroot()

for c in root.findall(MW_NS+'page'):
    wiki_title = c.find(MW_NS+'title')
    wiki_ns = c.find(MW_NS+'ns')
    
    # salta pagine senza titolo
    if wiki_title is None:
        continue

    # salta pagine non in NameSpace 0 (discussioni, utenti, template, etc)
    if wiki_ns.text != "0":
        continue
    
    lemma = wiki_title.text.strip()
        
    # salta locuzioni, parole composte o espressioni idiomatiche
    if lemma.find(" ") > -1:
        continue
    if lemma.find("-") > -1:
        continue	
    if lemma.find("'") > -1:
        continue

    wiki_revision = c.find(MW_NS+'revision')

    # salta pagine senza revisioni
    if wiki_revision is None:
        continue

    # salta pagine senza testo
    wiki_text = wiki_revision.find(MW_NS+'text')
    if wiki_text is None:
        continue

    start_it = wiki_text.text.find("{{-it-}}")

    # salta pagine senza definizione in italiano
    if wiki_text.text.find("{{-it-}}") < 0:
        continue

    wiki_text = wiki_text.text[start_it:]                
    start_sill = wiki_text.find(SILL_TPL)

    # salta pagine senza sillabazione
    if start_sill < 0:
        continue

    # salta pagine con sillabazione in altre lingue
    other_lang_start1 = wiki_text[10:].find("== {{-")
    if other_lang_start1 > 0 and start_sill > other_lang_start1:
        continue

    other_lang_start2 = wiki_text[10:].find("=={{-")
    if other_lang_start2 > 0 and start_sill > other_lang_start2:
        continue
        
    end_sill = wiki_text[start_sill + len(SILL_TPL) + 3:].find("\n")
    hyph1 = wiki_text[start_sill+len(SILL_TPL):start_sill+len(SILL_TPL)+end_sill+3].strip()

    # salta pagine con codice html o template nella sillabazione
    if hyph1.find("<") > -1 or hyph1.find(">") > -1 or hyph1.find("!") > -1 or hyph1.find("{") > -1:
        continue

    # salta pagine con sillabazione vuota
    if len(hyph1) < 1:
        continue

    # toglie le glosse tra parentesi per la disambiguazione dei termini
    p = re.compile(r'\([^)]*\)')
    hyph1 = re.sub(p, '', hyph1)
    hyph1 = hyph1.split(",")[0]

    # elimina spazi, punto e virgola iniziale e doppia pipe
    hyph1 = hyph1.replace(" ", "")
    hyph1 = hyph1.replace(";", "")
    hyph1 = hyph1.replace("||", "|" )

    # sostituisce nella sillabazione | con - per separare le sillabe
    hyph1 = hyph1.replace("|", "-")
    hyph1 = hyph1.replace("--", "-")

    # per sillabazioni ambigue tiene solo la prima
    hyph1 = hyph1.split("'o'")[0]

    # toglie apostrofi e asterischi
    hyph1 = hyph1.replace("'", "")
    hyph1 = hyph1.replace("*", "")

    # salta se non è rimasto testo
    if len(hyph1) < 1:
        continue

    # salta se il lemma non è sillababile
    if hyph1.find("nonsillababile") > -1:
        continue

    # toglie nella sillabazione accenti tonici (tranne ultima sillaba)
    hyph1 = hyph1.lower()
    last_char = hyph1[-1]
    hyph1 = hyph1[:-1]
    
    if not args.accenti:
        hyph1 = hyph1.replace("à", "a")
        hyph1 = hyph1.replace("á", "a")
        hyph1 = hyph1.replace("è", "e")
        hyph1 = hyph1.replace("é", "e")
        hyph1 = hyph1.replace("ì", "i")
        hyph1 = hyph1.replace("í", "i")
        hyph1 = hyph1.replace("ò", "o")
        hyph1 = hyph1.replace("ó", "o")
        hyph1 = hyph1.replace("ù", "u")
        hyph1 = hyph1.replace("ú", "u")
    
    hyph1 += last_char
    
    wiki_link = "https://it.wiktionary.org/wiki/"+wiki_title.text

    # inserisce nel db sqlite3 oppure stampa lemma, sillabazione e link alla pagina del wikizionario
    if args.sql:
        cur.execute("INSERT INTO " + args.table + " (`lemma`, `link`, `sillabazione`) VALUES (?, ?, ?)", (lemma, wiki_link, hyph1))
    else:
        if args.link:
            print(lemma + "," + hyph1 + "," + wiki_link)
        else:
            print(lemma + "," + hyph1)


if args.sql:
    con.commit()
    cur.execute("VACUUM `main`"); 
    con.commit()
    cur.close()
    con.close()
