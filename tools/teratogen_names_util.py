"""Shared by tools/build-teratogen-names.py and tools/build-teratogen-tis-links.py: one key per substance
whatever the language or salt, so "acide valproïque", "valproate de sodium", "Valproinsäure" and
"valproic acid" are recognised as one substance, and "hydroxyurea" is never taken for "hydroxychloroquine"."""
import re
import unicodedata

FORMS = re.compile(r"\b(tablets?|capsules?|cream|gel|injections?|infusion|eye drops|nasal spray|inhaler|patch(es)?|"
                   r"use of|in pregnancy|oral|topical|vaginal|for .*)\b")
SALTS = re.compile(r"\b(hydrochloride|dihydrochloride|chlorhydrate|dichlorhydrate|hydrobromide|bromhydrate|sulfate|sulphate|"
                   r"sodium|sodique|disodique|monosodique|potassium|potassique|dipotassium|dipotassique|"
                   r"acetate|citrate|phosphate|mesylate|mesilate|tartrate|maleate|fumarate|succinate|hyclate|"
                   r"(mono|di|tri|hemi|sesqui|hepta)?hydratee?|anhydre|anhydrous|calcium|calcique|lysine|arginine|base|carbonate|"
                   r"(di)?propionate|decanoate|(un)?decanoate|enanthate|enantate|cypionate|caproate|pivalate|tosilate|besilate|besylate|"
                   r"camphosulfonate|metasulfobenzoate|tetrachlorhydrate|tetrahydrochloride|erbumine|tert.?butylamine|de|d|di)\b")


def fold(s):
    s = s.lower().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def skel(s):
    """A spelling-free key for a substance name in English, French, German, Spanish or Italian."""
    s = fold(s).replace("'", " ").replace("’", " ")
    s = SALTS.sub(" ", FORMS.sub(" ", s))
    s = re.sub(r"\b(\w+)ique \(acide\)", r"acide \1ique", s)        # salicylique (acide) -> acide salicylique
    s = s.replace("desoxy", "deoxy")
    s = re.sub(r"\bacide (\w+)ique\b", r"\1ic acid", s)            # acide valproique -> valproic acid
    s = re.sub(r"\bacido (\w+)ico\b", r"\1ic acid", s)             # acido valproico -> valproic acid
    s = re.sub(r"(\w+?)(in)?saeure\b", r"\1ic acid", s)             # valproinsaeure -> valproic acid
    s = re.sub(r"(\w+)ic acid\b", r"\1ate", s)                      # valproic acid -> valproate, its salts' name
    s = re.sub(r"[^a-z0-9]", "", s)
    s = s.replace("ph", "f").replace("th", "t").replace("y", "i").replace("z", "c").replace("k", "c")
    s = re.sub(r"(ate|ide|one|ine|ole|e)$", lambda m: m.group(1)[:-1], s)
    return s.rstrip("e")
