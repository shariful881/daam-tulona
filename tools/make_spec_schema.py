"""প্রোডাক্টের ধরন অনুযায়ী 'এক নজরে' কোন কোন তথ্য দেখাবে, তার তালিকা বানায় -> config/spec_schema.json

প্রতিটা ঘর (field):
  bn    বাংলা নাম
  k     রেজেক্স; স্টোরের স্পেক টেবিলের "সেকশন > কী" (ছোট হাতের) লেখার সাথে মেলানো হয়।
        ফিচার লাইনের (সেকশন ছাড়া) ক্ষেত্রে লেখাটা " > কী"।
  x     এই রেজেক্স মিললে বাদ (যেমন ক্যামেরার "resolution" যেন ডিসপ্লেতে না যায়)
  m     একাধিক সারি মিললে কয়টা জোড়া লাগবে (যেমন ডিসপ্লে = সাইজ + ধরন + রেজোলিউশন)
  n,f   স্পেক না পেলে প্রোডাক্টের নাম থেকে বের করার রেজেক্স ও ফরম্যাট ({} = প্রথম গ্রুপ)
  b,bf  ব্র্যান্ড স্টোরের (Walton/Minister) স্পেক থেকে কোন কী, কোন ফরম্যাটে
চালানো: python -m tools.make_spec_schema
"""
import json
from pathlib import Path


def F(id, bn, k, n=None, f="{}", m=1, x=None, b=None, bf="{}"):
    d = {"id": id, "bn": bn, "k": k}
    if m > 1:
        d["m"] = m
    if x:
        d["x"] = x
    if n:
        d["n"], d["f"] = n, f
    if b:
        d["b"], d["bf"] = b, bf
    return d


# বারবার লাগে এমন ঘর
INCH = r"(\d{2,3}(?:\.\d)?)\s?(?:\"|”|''|’’|-?inch\b|ইঞ্চি)"
WARRANTY = F("warranty", "ওয়ারেন্টি", [r"> *(manufacturing )?warranty$", r"^warranty"])
COLOR = F("color", "রং", [r"> *colou?r\(?s?\)?$"])
WEIGHT = F("weight", "ওজন", [r"> *(net )?weight"])
CONN = F("connectivity", "কানেকশন", [r"> *connectivity$", r"> *connection( type)?$", r"> *wireless( technology)?$"], m=2,
         n=r"\b(wireless|bluetooth|wired|2\.4\s?g)\b")
BATTERY_LIFE = F("battery", "ব্যাটারি", [r"> *battery", r"> *play ?(back)? ?time", r"> *(music|working) time"], m=2,
                 n=r"(\d{3,5}\s?mah)")
FEATURES = F("features", "অন্যান্য ফিচার", [r"^ *> *(key |other |special |main )?features?$", r"> *highlights?$"])
CAPACITY_GB = F("capacity", "ক্যাপাসিটি", [r"> *(storage |memory )?capacity$", r"> *storage$"], n=r"\b(\d+\s?(?:gb|tb))\b")

laptop = [
    F("processor", "প্রসেসর", [r"> *processor( model)?$", r"> *cpu$", r"^processor > *(processor )?(brand|model|generation)"], m=2,
      n=r"\b((?:intel )?core\s?(?:ultra\s?)?[3579i](?:[\s-]?\d{3,5}\w*)?|ryzen\s?\d(?:\s?(?:pro\s?)?\d{3,4}\w*)?|celeron\s?\w*\d\w*|pentium\s?(?:silver|gold)?\s?\w*\d\w*|apple m\d(?:\s?(?:pro|max))?|snapdragon\s?x?\s?\w*)"),
    F("ram", "র‍্যাম", [r"> *ram$", r"^memory > *(ram|capacity)$", r"> *(installed )?memory$", r"> *ram (type|capacity)", r"^memory > *(type|bus speed)$"], m=2,
      x=[r"slot", r"max"], n=r"\b(\d{1,2}\s?gb)(?:\s?(?:ddr\d\w*|lpddr\d\w*|unified|ram))", f="{} RAM"),
    F("storage", "স্টোরেজ", [r"> *storage$", r"^storage > *(storage )?(type|capacity)$", r"> *ssd$", r"> *hdd$"], m=2,
      x=[r"slot", r"upgrade"], n=r"\b(\d+\s?(?:gb|tb)\s?(?:nvme\s?|m\.2\s?|pcie\s?)*(?:ssd|hdd|emmc))"),
    F("display", "ডিসপ্লে", [r"> *display$", r"> *screen$", r"^display > *(display )?(size|type|resolution)$"], m=3,
      x=[r"camera", r"webcam", r"port", r"output"], n=INCH, f="{} ইঞ্চি"),
    F("graphics", "গ্রাফিক্স", [r"> *graphics?( model| card| chipset)?$", r"> *gpu$", r"^graphics > *(graphics )?memory$"], m=2,
      n=r"\b((?:rtx|gtx|rx)\s?\d{3,4}\w*(?:\s?ti)?)"),
    F("ports", "পোর্ট", [r"> *(usb|type-?c|thunderbolt|hdmi)", r"> *ports?$", r"> *i/?o ports?"], m=4, x=[r"optical"]),
    F("network", "ওয়াইফাই/ব্লুটুথ", [r"> *wi-?fi", r"> *wlan", r"> *bluetooth"], m=2),
    F("battery", "ব্যাটারি", [r"> *battery( capacity| type)?$", r"> *battery life"], m=2),
    F("os", "অপারেটিং সিস্টেম", [r"> *(operating system|os)$"]),
    F("keyboard", "কিবোর্ড", [r"> *keyboard( type)?$", r"> *backlit"]),
    WEIGHT, FEATURES, WARRANTY,
]

desktop = [laptop[0], laptop[1], laptop[2], laptop[4],
           F("motherboard", "মাদারবোর্ড", [r"> *motherboard$", r"> *chipset$"]),
           F("psu", "পাওয়ার সাপ্লাই", [r"> *(power supply|psu)$"]),
           laptop[3], laptop[5], laptop[6], laptop[8], FEATURES, WARRANTY]

phone = [
    F("display", "ডিসপ্লে", [r"^display > *(size|type|resolution)$", r"> *display( size| type)?$", r"> *screen( size)?$"], m=3,
      x=[r"camera"], n=r"(\d\.\d{1,2})\s?(?:\"|inch)", f="{} ইঞ্চি"),
    F("chipset", "প্রসেসর/চিপসেট", [r"> *chipset$", r"> *processor$", r"> *cpu$", r"^(processor|platform) > *(chipset|cpu)$"], m=1,
      n=r"\b(snapdragon\s?[\w+ ]{1,12}|dimensity\s?\d{3,4}\w*|helio\s?\w\d{2,3}|exynos\s?\d{3,4}|unisoc\s?\w+|a1\d\s?(?:pro|bionic)?)"),
    F("ram", "র‍্যাম", [r"> *ram$", r"^memory > *ram"], n=r"\b(\d{1,2})(?:\s?gb)?\s?[/+]\s?\d{2,4}\s?(?:gb|tb)|\b(\d{1,2})\s?gb\s?ram", f="{}GB"),
    F("storage", "স্টোরেজ", [r"> *(internal )?storage$", r"> *rom$", r"^memory > *(internal|storage)"], n=r"[/+]\s?(\d{2,4}\s?(?:gb|tb))"),
    F("camera", "পেছনের ক্যামেরা", [r"> *(rear|back|main|primary) camera", r"> *cameras?$", r"^(main|rear|back) camera > *(resolution|camera|triple|dual|quad|single)"], m=1),
    F("selfie", "সামনের ক্যামেরা", [r"> *(front|selfie|secondary) camera", r"^(selfie|front) camera > *(resolution|camera|single)"], m=1),
    F("battery", "ব্যাটারি", [r"> *battery( capacity| type)?$", r"^battery > *(type|capacity)"], n=r"(\d{4,5}\s?mah)"),
    F("charging", "চার্জিং", [r"> *(fast )?charging", r"^battery > *charging"]),
    F("network", "নেটওয়ার্ক", [r"> *network( type| technology)?$", r"> *5g", r"> *sim( card)?$"], m=2, n=r"\b(5g|4g)\b"),
    F("os", "অপারেটিং সিস্টেম", [r"> *(operating system|os)$"]),
    FEATURES, WARRANTY,
]

feature_phone = [phone[0], F("sim", "সিম", [r"> *sim"]), phone[6], phone[4], F("memory", "মেমরি", [r"> *(memory|storage)"]), FEATURES, WARRANTY]

processor = [
    F("socket", "সকেট", [r"> *(cpu )?socket", r"^supported sockets"]),
    F("cores", "কোর / থ্রেড", [r"> *(no\.? of |total )?cores?( count)?$", r"> *threads?$", r"> *core\s?/\s?thread"], m=2),
    F("base", "বেস ক্লক", [r"> *base (clock|frequency|speed)", r"> *(clock )?speed$", r"> *processor base"]),
    F("boost", "সর্বোচ্চ ক্লক", [r"> *(max(imum)?|boost|turbo).*(clock|frequency|speed)"]),
    F("cache", "ক্যাশ", [r"> *(total )?(l3 |smart )?cache", r"> *l2 cache"]),
    F("tdp", "TDP (বিদ্যুৎ)", [r"> *(default |max )?tdp", r"> *thermal design"]),
    F("igpu", "বিল্ট-ইন গ্রাফিক্স", [r"> *(processor |integrated )?graphics"]),
    F("memory", "র‍্যাম সাপোর্ট", [r"> *memory (type|speed|support)"], m=2),
    F("cooler", "কুলার সাথে", [r"> *cpu cooler"]),
    WARRANTY,
]

motherboard = [
    F("socket", "সকেট", [r"> *(cpu )?socket", r"> *supported cpu"], n=r"\b(lga\s?\d{4}|am[45])\b"),
    F("chipset", "চিপসেট", [r"> *chipset$"], n=r"\b([abhxzq]\d{3}\w?)\b"),
    F("form", "সাইজ (ফর্ম ফ্যাক্টর)", [r"> *form factor", r"> *size$"], n=r"\b(micro[\s-]?atx|m-?atx|mini[\s-]?itx|e-?atx|atx)\b"),
    F("memory", "র‍্যাম সাপোর্ট", [r"> *memory( type| slots?| support)?$", r"> *(max|maximum) memory", r"> *dimm"], m=2, n=r"\b(ddr\d)\b"),
    F("m2", "M.2 স্লট", [r"> *m\.?2"], m=2),
    F("pcie", "PCIe স্লট", [r"> *(pci-?e|expansion slots?)"], m=2),
    F("network", "ল্যান / ওয়াইফাই", [r"> *(lan|ethernet|wi-?fi|wireless)"], m=2, n=r"\b(wifi\s?\d\w*|wi-fi)\b"),
    F("ports", "পেছনের পোর্ট", [r"> *(rear|back) (panel|i/?o)", r"> *usb"], m=2),
    WARRANTY,
]

gpu = [
    F("gpu", "জিপিইউ", [r"> *(graphics engine|chipset|gpu)$"], n=r"\b((?:rtx|gtx|rx|arc)\s?[a-z]?\d{3,4}\w*(?:\s?(?:ti|super|xt|xtx))?)"),
    F("vram", "ভিডিও মেমরি", [r"> *video memory$", r"> *memory (size|type)$", r"^video memory specifications > *(size|type)", r"> *(size|type)$"], m=2,
      x=[r"bus", r"display"], n=r"\b(\d{1,2}\s?gb)(?:\s?g?ddr\d\w*)?", f="{}"),
    F("bus", "মেমরি বাস", [r"> *memory (interface|bus)"]),
    F("clock", "ক্লক স্পিড", [r"> *(core|engine|boost|base|gpu) clock"], m=2),
    F("cores", "CUDA / স্ট্রিম কোর", [r"> *(cuda cores|stream processors?)"]),
    F("ports", "ডিসপ্লে পোর্ট", [r"> *(hdmi|display ?port|dvi|d-sub)"], m=3),
    F("psu", "সুপারিশকৃত PSU", [r"> *recommended (psu|power)", r"> *(power )?consumption"], m=1),
    F("connector", "পাওয়ার কানেক্টর", [r"> *(power )?connectors?$"]),
    F("size", "দৈর্ঘ্য / আকার", [r"> *(dimensions?|card length)"]),
    WARRANTY,
]

ram = [
    F("capacity", "ক্যাপাসিটি", [r"> *(memory )?capacity$"], n=r"\b(\d{1,3}\s?gb)\b"),
    F("type", "টাইপ", [r"> *(memory )?type$"], n=r"\b(l?pddr\d\w?|ddr\d\w?)\b"),
    F("speed", "স্পিড (বাস)", [r"> *(memory )?(frequency|speed|bus)"], n=r"\b(\d{4})\s?(?:mhz|bus|mt/s)?\b", f="{}MHz"),
    F("latency", "ল্যাটেন্সি", [r"> *(cas )?latency", r"> *voltage & cas"]),
    F("voltage", "ভোল্টেজ", [r"> *(operating )?voltage$"]),
    F("form", "ফর্ম", [r"> *form factor", r"> *pin$"], m=2),
    F("heatsink", "হিটসিংক / RGB", [r"> *heat ?sink", r"> *(rgb|lighting)"], m=2, n=r"\b(rgb)\b"),
    WARRANTY,
]

ssd = [
    CAPACITY_GB,
    F("interface", "ইন্টারফেস", [r"> *interface( type)?$"], n=r"\b(pcie\s?(?:gen\s?)?\d(?:\.\d)?(?:\s?x\d)?|nvme|sata\s?(?:iii|3)?|usb\s?\d(?:\.\d)?\w*)"),
    F("form", "ফর্ম ফ্যাক্টর", [r"> *fr?om factor"], n=r"\b(m\.2\s?\d{4}|m\.2|2\.5\")"),
    F("read", "রিড স্পিড", [r"> *(sequential |seq\.? )?read( speed)?$", r"> *sequential r/w", r"> *seq\.? read/ ?write"], m=1),
    F("write", "রাইট স্পিড", [r"> *(sequential |seq\.? )?write( speed)?$"]),
    F("flash", "ফ্ল্যাশ টাইপ", [r"> *(flash|nand)( type)?$"]),
    F("endurance", "টেকসইতা (TBW/MTBF)", [r"> *(tbw|mtbf|endurance)"], m=2),
    F("transfer", "ট্রান্সফার স্পিড", [r"> *(transfer|data transfer) (rate|speed)"]),
    WARRANTY,
]

hdd = [
    CAPACITY_GB,
    F("interface", "ইন্টারফেস", [r"> *interface( type)?$"], n=r"\b(sata\s?(?:iii|3)?|usb\s?\d(?:\.\d)?\w*|type-?c)"),
    F("rpm", "RPM", [r"> *(rpm|rotational speed|spindle)"], n=r"\b(\d{4})\s?rpm", f="{} RPM"),
    F("cache", "ক্যাশ", [r"> *(cache|buffer)"], n=r"\b(\d{2,3}\s?mb)\s?cache"),
    F("form", "সাইজ", [r"> *form factor"], n=r"(3\.5|2\.5)\s?(?:\"|inch)", f="{} ইঞ্চি"),
    F("transfer", "ট্রান্সফার স্পিড", [r"> *(transfer|data transfer) (rate|speed)", r"> *read"]),
    WARRANTY,
]

psu = [
    F("watt", "ক্ষমতা (ওয়াট)", [r"> *(total |continuous |rated )?(power|output capacity|wattage)$", r"> *total output"], n=r"\b(\d{3,4})\s?w(?:att)?\b", f="{}W"),
    F("cert", "এফিসিয়েন্সি সার্টিফিকেশন", [r"> *certifications?$", r"> *80 ?plus"], n=r"(80\s?\+?\s?(?:plus)?\s?(?:bronze|silver|gold|platinum|titanium|white))"),
    F("modular", "মডুলার", [r"> *modular"], n=r"\b((?:fully|semi|full)[\s-]?modular|non[\s-]?modular)"),
    F("fan", "ফ্যান সাইজ", [r"> *fan size"]),
    F("pcie", "PCIe কানেক্টর", [r"> *pci-?e"], m=1),
    F("protection", "সুরক্ষা", [r"> *protections?"]),
    F("form", "ফর্ম ফ্যাক্টর", [r"> *form factor", r"> *type$"]),
    WARRANTY,
]

casing = [
    F("type", "কেসিং ধরন", [r"> *(case |chassis )?type$", r"> *form factor$"], n=r"\b(mid[\s-]?tower|full[\s-]?tower|mini[\s-]?tower|micro[\s-]?atx|mini[\s-]?itx)"),
    F("mb", "মাদারবোর্ড সাপোর্ট", [r"> *(motherboard|mainboard) support"]),
    F("fans", "আগে থেকে লাগানো ফ্যান", [r"> *pre-? ?install(ed)? fans?"]),
    F("fan_support", "ফ্যান সাপোর্ট", [r"> *fans? support"]),
    F("radiator", "রেডিয়েটর সাপোর্ট", [r"> *radiator"]),
    F("gpu_len", "সর্বোচ্চ গ্রাফিক্স কার্ড", [r"> *maximum graphics card", r"> *vga (length|clearance)"]),
    F("cooler_h", "সর্বোচ্চ কুলার উচ্চতা", [r"> *maximum cpu cooler", r"> *cpu cooler (height|clearance)"]),
    F("panel", "সাইড প্যানেল", [r"> *(side panel|tempered\s+glass)"]),
    F("ports", "সামনের পোর্ট", [r"> *front (ports?|i/?o)", r"> *i/?o (ports?|panel)", r"> *ports$"]),
    WARRANTY,
]

cooler = [
    F("type", "ধরন", [r"> *type$"], n=r"\b(liquid|aio|air)\b"),
    F("socket", "সকেট সাপোর্ট", [r"> *(support(ed)? sockets?|socket)", r"^supported sockets > *(intel|amd)"], m=2),
    F("radiator", "রেডিয়েটর", [r"> *radiator"], n=r"\b(120|240|280|360|420)\s?mm", f="{}mm"),
    F("fan", "ফ্যান সাইজ / স্পিড", [r"> *fan (size|speed)", r"> *speed$"], m=2),
    F("airflow", "এয়ারফ্লো", [r"> *(fan )?(max )?air ?flow"]),
    F("noise", "শব্দ", [r"> *noise"]),
    F("tdp", "TDP", [r"> *tdp"]),
    F("light", "লাইটিং", [r"> *(led|lighting|rgb)"], n=r"\b(a?rgb)\b"),
    WARRANTY,
]

fan = [
    F("size", "সাইজ", [r"> *(fan )?size$"], n=r"\b(120|140|92|80|200)\s?mm", f="{}mm"),
    F("speed", "স্পিড", [r"> *(fan )?speed"]),
    F("airflow", "এয়ারফ্লো", [r"> *air ?flow"]),
    F("noise", "শব্দ", [r"> *noise"]),
    F("connector", "কানেক্টর", [r"> *connector"]),
    F("light", "লাইটিং", [r"> *(led|lighting)"], n=r"\b(a?rgb)\b"),
    F("pack", "প্যাকে কয়টা", [r"> *(quantity|pack)"], n=r"\b(\d)\s?(?:in\s?1|pcs|pack)", f="{}টা"),
    WARRANTY,
]

monitor = [
    F("size", "স্ক্রিন সাইজ", [r"> *(display |screen |panel )?size$"], x=[r"pixel"], n=INCH, f="{} ইঞ্চি"),
    F("resolution", "রেজোলিউশন", [r"> *(max(imum)? |native )?resolution$"], n=r"\b(fhd|qhd|uhd|4k|2k|wqhd|\d{3,4}\s?x\s?\d{3,4})\b"),
    F("panel", "প্যানেল", [r"> *panel( type)?$", r"> *display type$"], n=r"\b(ips|va|tn|oled|qd-?oled)\b"),
    F("refresh", "রিফ্রেশ রেট", [r"> *refresh rate"], n=r"\b(\d{2,3})\s?hz\b", f="{}Hz"),
    F("response", "রেসপন্স টাইম", [r"> *response time"]),
    F("brightness", "ব্রাইটনেস", [r"> *brightness"]),
    F("ports", "পোর্ট", [r"> *(i/?o )?ports?$", r"> *(hdmi|display ?port|vga|d-sub|usb)"], m=3, x=[r"frequency"]),
    F("hdr", "HDR / কালার", [r"> *(hdr|color gamut|colou?r space|colou?r gamut|srgb|dci)"], m=1),
    F("speaker", "স্পিকার", [r"> *speakers?"]),
    WARRANTY,
]

tv = [
    F("size", "স্ক্রিন সাইজ", [r"> *(display |screen )?size$"], n=INCH, f="{} ইঞ্চি"),
    F("type", "ডিসপ্লে ধরন", [r"> *(display|panel|screen) type", r"> *display technology"], n=r"\b(qled|oled|neo qled|mini ?led|nanocell|led|lcd)\b"),
    F("resolution", "রেজোলিউশন", [r"> *resolution"], n=r"\b(4k|uhd|fhd|full hd|hd ready|8k|hd)\b"),
    F("smart", "স্মার্ট / অপারেটিং সিস্টেম", [r"> *(operating system|os|platform|smart (tv|feature))"], m=1,
      n=r"\b(google tv|android tv|android|webos|tizen|vidaa|smart)\b"),
    F("refresh", "রিফ্রেশ রেট", [r"> *refresh rate", r"> *motion"]),
    F("hdr", "HDR", [r"> *hdr"]),
    F("sound", "সাউন্ড", [r"> *(sound|audio|speaker)( output| power)?"], m=1),
    F("ports", "পোর্ট", [r"> *(hdmi|usb)( ports?)?"], m=2),
    F("wireless", "ওয়াইফাই / ব্লুটুথ", [r"> *(wi-?fi|bluetooth|wireless)"], m=2),
    F("power", "বিদ্যুৎ খরচ", [r"> *power consumption"]),
    WARRANTY,
]

ac = [
    F("ton", "ক্ষমতা (টন)", [r"> *(capacity|ton)$"], n=r"(\d(?:\.\d)?)\s?ton", f="{} টন"),
    F("type", "ধরন", [r"> *type$"], n=r"\b(split|window|portable|cassette|ceiling)\b"),
    F("inverter", "ইনভার্টার", [r"> *inverter"], n=r"\b(inverter|non[\s-]?inverter)\b"),
    F("btu", "কুলিং ক্ষমতা (BTU)", [r"> *(cooling capacity|btu)"], n=r"\b(\d{4,5})\s?btu", f="{} BTU"),
    F("power", "বিদ্যুৎ খরচ", [r"> *(power consumption|rated power|input power)"]),
    F("coverage", "কত বড় ঘরের জন্য", [r"> *(room size|coverage|area)"]),
    F("refrigerant", "রেফ্রিজারেন্ট গ্যাস", [r"> *(refrigerant|gas)"], n=r"\b(r-?32|r-?410a?|r-?22)\b"),
    F("feature", "বিশেষ ফিচার", [r"> *(special |key )?features?$", r"> *(wifi|smart)"], m=2),
    F("warranty", "ওয়ারেন্টি", [r"> *compressor", r"> *warranty"], m=2),
]

fridge = [
    F("volume", "মোট ক্ষমতা", [r"> *(gross )?(volume|capacity)"], n=r"(\d{2,4})\s?(?:l|ltr|liter|litre)\b", f="{} লিটার", b="capacity", bf="{} লিটার"),
    F("net", "ব্যবহারযোগ্য ক্ষমতা", [r"> *net (volume|capacity)"], b="net", bf="{} লিটার"),
    F("type", "ধরন", [r"> *(type|cooling (type|system))$"], n=r"\b(no[\s-]?frost|direct[\s-]?cool|frost[\s-]?free|side[\s-]?by[\s-]?side|deep freezer|chest freezer)\b", b="type"),
    F("inverter", "ইনভার্টার", [r"> *inverter"], n=r"\b(inverter)\b", b="inverter", bf="{}"),
    F("doors", "দরজা", [r"> *(door|no\.? of doors?)"], n=r"\b(single|double|triple|four|side by side)[\s-]?door", f="{} door"),
    F("energy", "বিদ্যুৎ খরচ / রেটিং", [r"> *(energy|power consumption|star rating)"]),
    F("refrigerant", "রেফ্রিজারেন্ট গ্যাস", [r"> *(refrigerant|gas)"], n=r"\b(r-?600a|r-?134a)\b"),
    F("color", "রং / ডিজাইন", [r"> *(colou?r|design|finish)"]),
    F("warranty", "কম্প্রেসর ওয়ারেন্টি", [r"> *compressor", r"> *warranty"], m=2, b="warranty"),
]

washer = [
    F("kg", "ক্ষমতা", [r"> *(washing )?capacity"], n=r"(\d{1,2}(?:\.\d)?)\s?kg", f="{} কেজি"),
    F("type", "ধরন", [r"> *type$"], n=r"\b(front[\s-]?load(?:ing)?|top[\s-]?load(?:ing)?|semi[\s-]?auto(?:matic)?|fully[\s-]?auto(?:matic)?|twin tub)"),
    F("rpm", "স্পিন স্পিড", [r"> *(spin speed|rpm)"], n=r"\b(\d{3,4})\s?rpm", f="{} RPM"),
    F("inverter", "ইনভার্টার মোটর", [r"> *(inverter|motor)"], n=r"\b(inverter|direct drive)\b"),
    F("programs", "ওয়াশ প্রোগ্রাম", [r"> *(wash )?programs?"]),
    F("dryer", "ড্রায়ার", [r"> *dry"]),
    F("power", "বিদ্যুৎ খরচ", [r"> *power"]),
    WARRANTY,
]

kitchen_cap = [  # ওভেন, এয়ার ফ্রায়ার, কুকার, ব্লেন্ডার, গিজার ইত্যাদি
    F("capacity", "ক্ষমতা", [r"> *capacity$", r"> *volume$"], n=r"(\d{1,3}(?:\.\d)?)\s?(?:l|ltr|liter|litre)\b", f="{} লিটার"),
    F("type", "ধরন", [r"> *type$"], n=r"\b(convection|grill|solo|microwave|electric|gas|digital|manual|instant)\b"),
    F("power", "বিদ্যুৎ (ওয়াট)", [r"> *(power|wattage|rated power)( consumption)?$"], n=r"\b(\d{3,4})\s?w(?:att)?\b", f="{}W"),
    F("temp", "তাপমাত্রা", [r"> *temperature"]),
    F("modes", "মোড / অটো মেনু", [r"> *(modes?|auto ?menu|programs?|functions?|speed settings?)"], m=2),
    F("jar", "জার / উপাদান", [r"> *(jars?|material|blade)"], m=2),
    WARRANTY,
]

fan_cooler = [
    F("type", "ধরন", [r"> *type$"], n=r"\b(ceiling|table|stand|wall|pedestal|rechargeable|exhaust|air cooler|tower)\b"),
    F("size", "সাইজ", [r"> *(size|sweep|blade)"], n=r"(\d{2})\s?(?:\"|inch|”)", f="{} ইঞ্চি"),
    F("power", "বিদ্যুৎ (ওয়াট)", [r"> *(power|wattage)"], n=r"\b(\d{2,3})\s?w\b", f="{}W"),
    F("battery", "ব্যাটারি ব্যাকআপ", [r"> *(battery|backup)"], m=2),
    F("speed", "স্পিড", [r"> *(speed|rpm)"]),
    F("tank", "পানির ট্যাংক", [r"> *(tank|water)"]),
    WARRANTY,
]

purifier = [
    F("type", "ধরন", [r"> *type$"], n=r"\b(ro|uv|uf|air purifier|water purifier|filter)\b"),
    F("stages", "ফিল্টার ধাপ", [r"> *(filter|stage|filtration)"], m=2, n=r"(\d{1,2})\s?stage", f="{} ধাপ"),
    F("capacity", "ক্ষমতা", [r"> *(capacity|tank|storage)"], n=r"(\d{1,2})\s?(?:l|ltr|liter)\b", f="{} লিটার"),
    F("coverage", "কত বড় ঘর", [r"> *(coverage|room size|cadr)"], m=2),
    F("power", "বিদ্যুৎ", [r"> *power"]),
    WARRANTY,
]

vacuum = [
    F("type", "ধরন", [r"> *type$"], n=r"\b(robot|handheld|cordless|canister|upright|wet|dry)\b"),
    F("power", "ক্ষমতা", [r"> *(power|wattage)$"], n=r"\b(\d{3,4})\s?w\b", f="{}W"),
    F("suction", "সাকশন", [r"> *suction"]),
    F("battery", "ব্যাটারি", [r"> *(battery|run ?time)"], m=2),
    F("dust", "ডাস্ট বক্স", [r"> *(dust|bin)"]),
    WARRANTY,
]

keyboard = [
    F("type", "ধরন", [r"> *(keyboard )?type$"], n=r"\b(mechanical|membrane|optical|magnetic)\b"),
    F("switch", "সুইচ", [r"> *switch( type)?"], n=r"\b((?:red|blue|brown|black|yellow|silver)\s?switch)"),
    CONN,
    F("layout", "লেআউট / কী", [r"> *(layout|keys?|number of keys)"], m=1, n=r"\b(tkl|60%|65%|75%|96%|full[\s-]?size)\b"),
    F("light", "ব্যাকলাইট", [r"> *(backlight|lighting|led|rgb)"], n=r"\b(rgb|backlit)\b"),
    BATTERY_LIFE, F("bangla", "বাংলা লেখা", [r"> *bangla"], n=r"\b(bangla)\b"), WARRANTY,
]

mouse = [
    F("dpi", "DPI", [r"> *(max )?dpi", r"> *resolution$"], n=r"\b(\d{3,5})\s?dpi", f="{} DPI"),
    F("sensor", "সেন্সর", [r"> *sensor"]),
    CONN,
    F("buttons", "বাটন", [r"> *(buttons?|number of buttons)"]),
    F("weight", "ওজন", [r"> *weight"]),
    BATTERY_LIFE,
    F("light", "লাইটিং", [r"> *(lighting|rgb|led)"], n=r"\b(rgb)\b"),
    WARRANTY,
]

audio = [  # হেডফোন, ইয়ারবাডস, নেকব্যান্ড, ইয়ারফোন
    F("type", "ধরন", [r"> *(type|form factor|wearing (style|type))$"], n=r"\b(over[\s-]?ear|on[\s-]?ear|in[\s-]?ear|tws|neckband|open[\s-]?ear)\b"),
    CONN,
    F("bt", "ব্লুটুথ ভার্সন", [r"> *bluetooth( version)?$", r"> *version$"], n=r"\b(?:bt|bluetooth)\s?v?(5\.\d)", f="Bluetooth {}"),
    F("driver", "ড্রাইভার", [r"> *driver( size| unit)?"], n=r"\b(\d{1,2}(?:\.\d)?)\s?mm", f="{}mm"),
    F("anc", "নয়েজ ক্যান্সেলেশন", [r"> *(anc|noise (cancel|reduction))"], m=2, n=r"\b(anc|enc|noise cancell?ing)\b"),
    F("battery", "ব্যাটারি / প্লেটাইম", [r"> *battery", r"> *play ?(back)? ?time", r"> *(music|talk|working) time", r"> *standby"], m=2),
    F("charging", "চার্জিং", [r"> *(charging|charge time|fast charg)"], m=1),
    F("mic", "মাইক্রোফোন", [r"> *mic(rophone)?"]),
    F("water", "পানি প্রতিরোধ", [r"> *(water|ip ?rating|waterproof)"], n=r"\b(ipx?\d)\b"),
    WARRANTY,
]

speaker = [
    F("power", "আউটপুট পাওয়ার", [r"> *(output|rms|total)( power)?$", r"> *power output", r"> *output power"], n=r"\b(\d{1,4})\s?w(?:att)?\b", f="{}W"),
    F("channel", "চ্যানেল", [r"> *channels?"], n=r"\b(2\.0|2\.1|5\.1|7\.1|3\.1)\b"),
    CONN,
    F("battery", "ব্যাটারি", [r"> *(battery|play ?time)"], m=2),
    F("freq", "ফ্রিকোয়েন্সি রেসপন্স", [r"> *frequency"]),
    F("water", "পানি প্রতিরোধ", [r"> *(waterproof|ip ?rating)"], n=r"\b(ipx?\d)\b"),
    WARRANTY,
]

webcam = [
    F("resolution", "রেজোলিউশন", [r"> *(video )?resolution", r"> *video"], n=r"\b(4k|2k|1080p|720p|1440p)\b"),
    F("fps", "ফ্রেম রেট", [r"> *(frame rate|fps)"], n=r"\b(\d{2})\s?fps", f="{} FPS"),
    F("focus", "ফোকাস", [r"> *focus"]),
    F("mic", "মাইক্রোফোন", [r"> *mic"]),
    F("fov", "দেখার কোণ", [r"> *(field of view|fov|angle)"]),
    F("connector", "কানেক্টর", [r"> *(connect|interface)"]),
    WARRANTY,
]

mic = [
    F("type", "ধরন", [r"> *type$"], n=r"\b(condenser|dynamic|lavalier|wireless|usb)\b"),
    F("pattern", "পোলার প্যাটার্ন", [r"> *polar"]),
    CONN,
    F("freq", "ফ্রিকোয়েন্সি রেসপন্স", [r"> *frequency"]),
    F("sample", "স্যাম্পল রেট", [r"> *(sample|bit) (rate|depth)"], m=2),
    WARRANTY,
]

flash = [  # পেন ড্রাইভ, মেমরি কার্ড
    CAPACITY_GB,
    F("interface", "ইন্টারফেস", [r"> *interface"], n=r"\b(usb\s?\d(?:\.\d)?\w*|type-?c|otg)\b"),
    F("read", "রিড স্পিড", [r"> *read"]),
    F("write", "রাইট স্পিড", [r"> *write"]),
    F("class", "ক্লাস", [r"> *(class|speed class|uhs)"], n=r"\b(class\s?10|u[13]|v30|a[12])\b"),
    WARRANTY,
]

power_bank = [
    F("mah", "ক্যাপাসিটি", [r"> *(battery )?capacity"], n=r"(\d{4,5})\s?mah", f="{} mAh"),
    F("output", "সর্বোচ্চ আউটপুট", [r"> *(max |total )?output", r"> *fast charging"], m=1, n=r"\b(\d{2,3})\s?w\b", f="{}W"),
    F("ports", "পোর্ট", [r"> *(ports?|usb|type-?c)"], m=2),
    F("input", "ইনপুট (চার্জ নেওয়া)", [r"> *input"]),
    F("wireless", "ওয়্যারলেস চার্জিং", [r"> *(wireless|magsafe|magnetic)"], n=r"\b(magsafe|wireless|magnetic)\b"),
    F("display", "ডিসপ্লে", [r"> *(display|indicator)"]),
    WARRANTY,
]

watch = [
    F("display", "ডিসপ্লে", [r"> *(display|screen)( size| type)?$"], m=2, n=r"(\d\.\d{1,2})\s?(?:\"|inch)", f="{} ইঞ্চি"),
    F("calling", "কলিং", [r"> *(calling|bluetooth call)"], n=r"\b(bluetooth calling|calling)\b"),
    F("battery", "ব্যাটারি", [r"> *battery", r"> *(standby|usage) time"], m=2),
    F("health", "স্বাস্থ্য সেন্সর", [r"> *(sensor|health|heart rate|spo2)"], m=2),
    F("water", "পানি প্রতিরোধ", [r"> *(water|ip ?rating|atm)"], n=r"\b(ip6\d|5\s?atm)\b"),
    F("compat", "যে ফোনে চলে", [r"> *(compatib|support(ed)? (os|system))"]),
    CONN, WARRANTY,
]

router = [
    F("standard", "ওয়াইফাই স্ট্যান্ডার্ড", [r"> *(wi-?fi )?standards?", r"> *wireless standard"], n=r"\b(wi-?fi\s?7|wi-?fi\s?6e?|wi-?fi\s?5|ax\d{3,5}|ac\d{3,4}|be\d{4,5}|n300)\b"),
    F("speed", "গতি", [r"> *(wireless |wi-?fi )?(speed|data rate)"], n=r"\b(\d{3,5})\s?mbps", f="{} Mbps"),
    F("band", "ব্যান্ড", [r"> *(frequency|band)"], n=r"\b(dual[\s-]?band|tri[\s-]?band|single[\s-]?band)\b"),
    F("ports", "পোর্ট", [r"> *(ports?|interface|lan|wan|ethernet)"], m=2, x=[r"standard"]),
    F("antenna", "অ্যান্টেনা", [r"> *antenna"]),
    F("coverage", "কভারেজ", [r"> *(coverage|range)"]),
    F("mesh", "মেশ / বিশেষ", [r"> *(mesh|easymesh|features?)$"], n=r"\b(mesh)\b"),
    WARRANTY,
]

switch = [
    F("ports", "পোর্ট", [r"> *(ports?|interface)"], m=2, n=r"\b(\d{1,2})[\s-]?port", f="{} পোর্ট"),
    F("speed", "গতি", [r"> *(speed|data rate|switching capacity)"], n=r"\b(gigabit|10/100|2\.5g|10g)\b"),
    F("poe", "PoE", [r"> *poe"], n=r"\b(poe\+?)\b"),
    F("managed", "ম্যানেজড", [r"> *(managed|management)"], n=r"\b((?:un)?managed|smart)\b"),
    F("form", "ডেস্কটপ / র‍্যাক", [r"> *(mounting|form|desktop|rack)"]),
    WARRANTY,
]

cam = [  # আইপি, সিসি, ওয়াইফাই ক্যামেরা
    F("resolution", "রেজোলিউশন", [r"> *(resolution|megapixel|image sensor)"], n=r"\b(\d{1,2}(?:\.\d)?\s?(?:mp|megapixel)|4k|1080p|2k)\b"),
    F("lens", "লেন্স", [r"> *lens"]),
    F("night", "রাতের দৃশ্য", [r"> *(night|ir |ir range|infrared|color ?vu|full color)"], m=2, n=r"\b(color night|full color|ir)\b"),
    F("audio", "অডিও", [r"> *(audio|two-?way|mic)"], m=1),
    F("storage", "রেকর্ডিং / স্টোরেজ", [r"> *(storage|sd card|micro ?sd)"]),
    F("ptz", "ঘোরানো (PTZ)", [r"> *(ptz|pan|tilt|rotation)"], m=2, n=r"\b(ptz|360)\b"),
    F("conn", "কানেকশন", [r"> *(connectivity|network|wi-?fi|poe)"], m=2),
    F("weather", "বাইরে ব্যবহার", [r"> *(weather|ip ?rating|waterproof)"], n=r"\b(ip6\d)\b"),
    WARRANTY,
]

dvr = [
    F("channels", "চ্যানেল", [r"> *(channels?|video input)"], n=r"\b(\d{1,2})[\s-]?(?:ch|channel)", f="{} চ্যানেল"),
    F("resolution", "রেকর্ড রেজোলিউশন", [r"> *(recording )?resolution"], m=1),
    F("hdd", "হার্ডডিস্ক স্লট", [r"> *(hdd|sata)( bays?| slots?| interface)?$", r"> *storage( bays?| slots?| capacity| interface)?$"], x=[r"temperature"]),
    F("output", "আউটপুট", [r"> *(video output|hdmi|vga)"], m=2),
    F("poe", "PoE", [r"> *poe"]),
    WARRANTY,
]

printer = [
    F("type", "ধরন", [r"> *(printer )?type$", r"> *print technology"], n=r"\b(laser|ink ?tank|inkjet|dot matrix|thermal|label)\b"),
    F("func", "কাজ", [r"> *(functions?|print, scan|all[\s-]?in[\s-]?one)"], n=r"\b(all[\s-]?in[\s-]?one|multifunction|mfp)\b"),
    F("color", "রঙিন / সাদাকালো", [r"> *(colou?r|mono|print colou?r)"], n=r"\b(colou?r|mono(?:chrome)?)\b", x=[r"colou?r\(?s?\)?$"]),
    F("speed", "প্রিন্ট স্পিড", [r"> *(print )?speed"], m=1, n=r"\b(\d{1,3})\s?ppm", f="{} পাতা/মিনিট"),
    F("resolution", "রেজোলিউশন", [r"> *(print )?resolution"]),
    F("duplex", "দুই পাশে প্রিন্ট", [r"> *duplex"], n=r"\b(duplex)\b"),
    F("conn", "কানেকশন", [r"> *(connectivity|interface|wi-?fi|network)"], m=2),
    F("cartridge", "কার্টিজ / টোনার", [r"> *(cartridge|toner|ink)"], m=1),
    WARRANTY,
]

scanner = [
    F("type", "ধরন", [r"> *(scanner )?type$"], n=r"\b(flatbed|sheet[\s-]?fed|document|portable|barcode)\b"),
    F("resolution", "রেজোলিউশন", [r"> *(optical )?resolution"]),
    F("speed", "স্পিড", [r"> *(scan )?speed"]),
    F("adf", "অটো ফিডার", [r"> *(adf|feeder)"]),
    F("conn", "কানেকশন", [r"> *(connectivity|interface)"]),
    WARRANTY,
]

projector = [
    F("lumens", "ব্রাইটনেস", [r"> *(brightness|lumens?)"], n=r"\b(\d{3,5})\s?(?:ansi\s?)?lumens?", f="{} লুমেন"),
    F("resolution", "রেজোলিউশন", [r"> *(native )?resolution"], n=r"\b(4k|1080p|fhd|wxga|xga|svga|720p)\b"),
    F("contrast", "কনট্রাস্ট", [r"> *contrast"]),
    F("tech", "প্রযুক্তি", [r"> *(display technology|technology|type)$"], n=r"\b(dlp|lcd|laser|led)\b"),
    F("lamp", "ল্যাম্পের আয়ু", [r"> *(lamp|light source) life"]),
    F("ports", "পোর্ট", [r"> *(hdmi|vga|usb|ports?|input)"], m=3),
    WARRANTY,
]

ups = [
    F("va", "ক্ষমতা", [r"> *(capacity|power rating|va|output power)"], m=2, n=r"\b(\d{3,5})\s?va\b", f="{} VA"),
    F("backup", "ব্যাকআপ", [r"> *(backup|back up|runtime)"], m=1),
    F("battery", "ব্যাটারি", [r"> *battery"], m=2),
    F("type", "ধরন", [r"> *(type|topology|technology)$"], n=r"\b(online|offline|line[\s-]?interactive|mini|dc)\b"),
    F("output", "আউটপুট", [r"> *(output|outlet|waveform)"], m=2),
    F("input", "ইনপুট ভোল্টেজ", [r"> *input"]),
    WARRANTY,
]

camera = [
    F("sensor", "সেন্সর", [r"> *(sensor|image sensor)( type| size)?$"], m=2, n=r"\b(full[\s-]?frame|aps-?c|micro four thirds)\b"),
    F("mp", "মেগাপিক্সেল", [r"> *(effective )?(pixels|megapixels?|resolution)$"], n=r"\b(\d{2,3}(?:\.\d)?)\s?mp\b", f="{} MP"),
    F("video", "ভিডিও", [r"> *(video|movie)( resolution| recording)?"], n=r"\b(8k|6k|4k|5\.3k|2\.7k|1080p)\b"),
    F("lens", "লেন্স", [r"> *(lens|mount|focal length)"], m=2),
    F("iso", "ISO", [r"> *iso"]),
    F("screen", "স্ক্রিন", [r"> *(screen|lcd|monitor|viewfinder)"], m=2),
    F("battery", "ব্যাটারি", [r"> *battery"]),
    F("stabil", "স্ট্যাবিলাইজেশন", [r"> *(stabili[sz]ation|ibis)"]),
    WARRANTY,
]

console = [
    F("storage", "স্টোরেজ", [r"> *storage"], n=r"\b(\d+\s?(?:gb|tb))\b"),
    F("edition", "এডিশন", [r"> *(edition|model|version)"], n=r"\b(digital|disc|slim|pro|oled|lite|standard)\b"),
    F("resolution", "রেজোলিউশন", [r"> *(resolution|output)"], n=r"\b(4k|8k|1080p)\b"),
    F("controller", "কন্ট্রোলার", [r"> *(controller|in the box)"]),
    CONN, WARRANTY,
]

gamepad = [
    F("platform", "যেটাতে চলে", [r"> *(compatib|platform|support)"], m=2, n=r"\b(ps5|ps4|xbox|pc|android|switch)\b"),
    CONN, BATTERY_LIFE, F("vibration", "ভাইব্রেশন", [r"> *(vibration|rumble|motor)"]), WARRANTY,
]

chair = [
    F("material", "উপাদান", [r"> *(material|upholstery|cover)"], m=2),
    F("recline", "হেলানো", [r"> *(recline|backrest|tilt)"], m=2),
    F("armrest", "হাতল", [r"> *arm ?rest"]),
    F("load", "সর্বোচ্চ ওজন", [r"> *(max(imum)? (load|weight)|load capacity|weight capacity)"]),
    F("size", "আকার", [r"> *(dimensions?|size|height)"], m=1),
    WARRANTY,
]

stabilizer = [
    F("capacity", "ক্ষমতা", [r"> *(capacity|rating|power)"], n=r"\b(\d{3,5})\s?(?:va|w)\b", f="{} VA"),
    F("input", "ইনপুট রেঞ্জ", [r"> *input"]),
    F("output", "আউটপুট", [r"> *output"]),
    F("type", "ধরন", [r"> *type$"], n=r"\b(servo|relay|digital|automatic)\b"),
    WARRANTY,
]

power_station = [
    F("capacity", "ব্যাটারি ক্ষমতা", [r"> *(battery )?capacity"], n=r"\b(\d{3,5})\s?wh\b", f="{} Wh"),
    F("output", "আউটপুট", [r"> *(ac )?output", r"> *rated power"], m=2, n=r"\b(\d{3,4})\s?w\b", f="{}W"),
    F("ports", "পোর্ট", [r"> *(ports?|outlets?|usb)"], m=2),
    F("charging", "চার্জ নেওয়া", [r"> *(charging|input|solar)"], m=2),
    F("battery", "ব্যাটারির ধরন", [r"> *(battery type|cell|chemistry)"], n=r"\b(lifepo4|lithium)\b"),
    WARRANTY,
]

light = [
    F("watt", "ওয়াট", [r"> *(power|wattage)"], n=r"\b(\d{1,3})\s?w\b", f="{}W"),
    F("type", "ধরন", [r"> *type$"], n=r"\b(led|bulb|tube|panel|strip|rechargeable|emergency|solar)\b"),
    F("color", "আলোর রং", [r"> *(colou?r temperature|light colou?r)"]),
    F("battery", "ব্যাটারি ব্যাকআপ", [r"> *(battery|backup)"], m=2),
    WARRANTY,
]

drone = [
    F("camera", "ক্যামেরা", [r"> *(camera|video resolution|sensor)"], m=2, n=r"\b(8k|6k|4k|2\.7k|1080p)\b"),
    F("flight", "ওড়ার সময়", [r"> *(flight time|max(imum)? flight)"]),
    F("range", "রেঞ্জ", [r"> *(range|transmission)"], m=1),
    F("weight", "ওজন", [r"> *(takeoff )?weight"]),
    F("gimbal", "গিম্বল", [r"> *gimbal"]),
    WARRANTY,
]

tv_box = [
    F("os", "অপারেটিং সিস্টেম", [r"> *(operating system|os)"], n=r"\b(android tv|google tv|android\s?\d{1,2})\b"),
    F("ram", "র‍্যাম / স্টোরেজ", [r"> *(ram|storage|rom|memory)"], m=2),
    F("resolution", "রেজোলিউশন", [r"> *(resolution|output)"], n=r"\b(4k|8k|1080p)\b"),
    F("conn", "কানেকশন", [r"> *(wi-?fi|bluetooth|connectivity)"], m=2),
    WARRANTY,
]

hub = [
    F("ports", "পোর্ট", [r"> *(ports?|interface|output)"], m=3, n=r"\b(\d{1,2})[\s-]?in[\s-]?1", f="{}-in-1"),
    F("input", "কানেক্টর", [r"> *(input|connector|host)"], n=r"\b(type-?c|usb[\s-]?c|usb\s?3\.\d|usb\s?2\.0)\b"),
    F("speed", "ডাটা স্পিড", [r"> *(data |transfer )?(speed|rate)"]),
    F("pd", "চার্জিং (PD)", [r"> *(power delivery|pd|charging)"], n=r"\b(\d{2,3})\s?w\b", f="{}W PD"),
    F("display", "ডিসপ্লে আউটপুট", [r"> *(hdmi|display|resolution)"], m=1),
    WARRANTY,
]

cable = [
    F("type", "ধরন", [r"> *(type|connector)"], m=2, n=r"\b(type-?c to (?:type-?c|lightning|usb)|usb to (?:type-?c|lightning|micro)|hdmi|displayport|lightning|micro usb|vga|cat\s?\d\w?|aux)\b"),
    F("length", "দৈর্ঘ্য", [r"> *(cable )?length"], n=r"\b(\d+(?:\.\d)?)\s?(?:m|meter|ft)\b", f="{} মিটার"),
    F("speed", "স্পিড / চার্জিং", [r"> *(speed|data|charging|power|resolution)"], m=2, n=r"\b(\d{2,3})\s?w\b", f="{}W"),
    WARRANTY,
]

PROFILES = {
    "laptop": (laptop, ["laptop", "gaming-laptop", "ultrabook", "ai-pc"]),
    "desktop": (desktop, ["gaming-pc", "brand-pc", "all-in-one-pc", "mini-pc", "mac-desktop", "desktop-pc", "workstation", "server"]),
    "phone": (phone, ["smartphone", "tablet"]),
    "feature_phone": (feature_phone, ["feature-phone"]),
    "processor": (processor, ["processor"]),
    "motherboard": (motherboard, ["motherboard"]),
    "gpu": (gpu, ["graphics-card"]),
    "ram": (ram, ["desktop-ram", "laptop-ram"]),
    "ssd": (ssd, ["ssd", "portable-ssd"]),
    "hdd": (hdd, ["hdd", "portable-hdd"]),
    "psu": (psu, ["power-supply"]),
    "casing": (casing, ["casing"]),
    "cooler": (cooler, ["cpu-cooler", "liquid-cooler"]),
    "fan": (fan, ["casing-fan"]),
    "monitor": (monitor, ["monitor-all", "gaming-monitor", "portable-monitor"]),
    "tv": (tv, ["tv"]),
    "ac": (ac, ["ac"]),
    "fridge": (fridge, ["fridge"]),
    "washer": (washer, ["washing-machine"]),
    "kitchen": (kitchen_cap, ["oven", "air-fryer", "cooker", "induction-stove", "blender", "geyser-heater", "iron", "sewing-machine"]),
    "fan_cooler": (fan_cooler, ["fan-cooler"]),
    "purifier": (purifier, ["water-air-purifier"]),
    "vacuum": (vacuum, ["vacuum-cleaner"]),
    "keyboard": (keyboard, ["keyboard"]),
    "mouse": (mouse, ["mouse"]),
    "audio": (audio, ["headphone", "bluetooth-headphone", "earbuds", "neckband", "earphone"]),
    "speaker": (speaker, ["speaker", "bluetooth-speaker", "soundbar"]),
    "webcam": (webcam, ["webcam"]),
    "mic": (mic, ["microphone"]),
    "flash": (flash, ["pen-drive", "memory-card"]),
    "power_bank": (power_bank, ["power-bank"]),
    "watch": (watch, ["smart-watch", "smart-band", "smart-ring"]),
    "router": (router, ["router", "gaming-router", "pocket-router", "range-extender", "access-point", "wifi-adapter", "lan-card", "starlink"]),
    "switch": (switch, ["network-switch", "poe-injector"]),
    "cam": (cam, ["wifi-camera", "ip-camera", "cc-camera", "ptz-camera", "solar-camera", "camera-package", "dash-cam"]),
    "dvr": (dvr, ["dvr-nvr"]),
    "printer": (printer, ["laser-printer", "printer", "special-printer", "photocopier"]),
    "scanner": (scanner, ["scanner"]),
    "projector": (projector, ["projector"]),
    "ups": (ups, ["online-ups", "mini-ups", "ups", "ips"]),
    "stabilizer": (stabilizer, ["voltage-stabilizer"]),
    "power_station": (power_station, ["power-station", "solar", "generator", "battery"]),
    "camera": (camera, ["dslr-mirrorless", "digital-camera", "action-camera"]),
    "console": (console, ["gaming-console", "vr"]),
    "gamepad": (gamepad, ["gamepad", "racing-wheel"]),
    "chair": (chair, ["gaming-chair", "gaming-desk"]),
    "light": (light, ["light", "monitor-light-bar"]),
    "drone": (drone, ["drone", "gimbal"]),
    "tv_box": (tv_box, ["tv-box"]),
    "hub": (hub, ["hub-dock", "converter", "card-reader", "enclosure", "capture-card"]),
    "cable": (cable, ["cable", "network-cable"]),
}
# যে ক্যাটাগরি কোনো প্রোফাইলে নেই (ব্যাগ, মাউস প্যাড, সফটওয়্যার…), সেখানে সাধারণ কয়েকটা ঘর
GENERIC = [F("type", "ধরন", [r"> *type$"]), F("size", "সাইজ", [r"> *(size|dimensions?)$"]),
           F("material", "উপাদান", [r"> *material"]), F("compat", "যেটার সাথে চলে", [r"> *(compatib|support)"]),
           COLOR, FEATURES, WARRANTY]


def main():
    for fields, _ in PROFILES.values():  # সব ধরনে শেষে "অন্যান্য ফিচার" (স্টোরের ফিচার লাইন যেন হারায় না)
        if not any(f["id"] == "features" for f in fields):
            fields.insert(len(fields) - 1 if fields and fields[-1]["id"] == "warranty" else len(fields), FEATURES)
    out = {"_নোট": "স্বয়ংক্রিয়ভাবে তৈরি (tools/make_spec_schema.py)। প্রোডাক্টের ধরন অনুযায়ী 'এক নজরে' কোন তথ্য দেখাবে।",
           "profiles": {k: v[0] for k, v in PROFILES.items()}, "generic": GENERIC,
           "category_profile": {c: k for k, v in PROFILES.items() for c in v[1]}}
    Path("config/spec_schema.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(len(out["profiles"]), "প্রোফাইল,", len(out["category_profile"]), "ক্যাটাগরি")


if __name__ == "__main__":
    main()
