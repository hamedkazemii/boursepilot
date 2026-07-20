def classify(text):

    text = text.replace("‌"," ")

    if (
        "طلا" in text
        or "پشتوانه طلا" in text
        or "كالاي" in text
    ):
        return "طلا"


    if (
        "اهرمي" in text
        or "اهرم" in text
    ):
        return "اهرم"


    if (
        "درآمد ثابت" in text
        or "درآمدثابت" in text
        or "ثابت" in text
    ):
        return "درآمد ثابت"


    if (
        "مختلط" in text
    ):
        return "مختلط"


    if (
        "سهام" in text
        or "سهامي" in text
    ):
        return "سهامی"


    return "UNKNOWN"
