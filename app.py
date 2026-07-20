from reports.report import MorningReport


def main():

    report = MorningReport()

    result = report.generate(
        "دارونو"
    )

    print(result)


if __name__ == "__main__":
    main()
