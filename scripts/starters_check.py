"""Check candidate starter pairs: print undirected and directed (back-only, newer->older) distances.
Usage: python -I scripts/starters_check.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import serve  # noqa: E402
import starters  # noqa: E402

CANDIDATES = [
    ("Marbury v. Madison", "United States v. Nixon", "Judicial review to the tapes"),
    ("Marbury v. Madison", "Bush v. Gore", "Who decides"),
    ("Dred Scott v. Sandford", "Loving v. Virginia", "Citizenship to marriage"),
    ("Plessy v. Ferguson", "Grutter v. Bollinger", "Separate to diverse"),
    ("Lochner v. New York", "Griswold v. Connecticut", "Liberty, twice"),
    ("Schenck v. United States", "Brandenburg v. Ohio", "Clear and present to imminent"),
    ("Schenck v. United States", "Texas v. Johnson", "Leaflets to flags"),
    ("Korematsu v. United States", "Hamdi v. Rumsfeld", "Wartime detention"),
    ("Gideon v. Wainwright", "Miranda v. Arizona", "Counsel to warnings"),
    ("Griswold v. Connecticut", "Obergefell v. Hodges", "Privacy to marriage"),
    ("Brown v. Board of Education", "Regents v. Bakke", "Desegregation to affirmative action"),
    ("Erie R. Co. v. Tompkins", "Bell Atlantic v. Twombly", "Civil procedure, start to finish"),
    ("Pennoyer v. Neff", "Carpenter v. United States", "Presence to cell towers"),
    ("Katz v. United States", "Kelo v. New London", "K to K"),
    ("Tinker v. Des Moines", "Citizens United v. FEC", "Armbands to super PACs"),
    ("Youngstown Sheet & Tube v. Sawyer", "Clinton v. Jones", "Presidents in court"),
    ("New York Times v. Sullivan", "Citizens United v. FEC", "Press to money"),
    ("Buck v. Bell", "Erie R. Co. v. Tompkins", "Holmes to Brandeis"),
    ("Civil Rights Cases", "Katz v. United States", "State action to phone booths"),
    ("Baker v. Carr", "Bush v. Gore", "Political thicket"),
    ("Daubert v. Merrell Dow", "District of Columbia v. Heller", "Experts to arms"),
    ("Bowers v. Hardwick", "Carpenter v. United States", "Bedrooms to cell sites"),
    ("Wickard v. Filburn", "NFIB v. Sebelius", "Wheat to health care"),
    ("Miranda v. Arizona", "Kelo v. New London", "Warnings to takings"),
    ("Roe v. Wade", "Planned Parenthood v. Casey", "Roe to Casey"),
    ("Mapp v. Ohio", "Carpenter v. United States", "Exclusion to location"),
    ("International Shoe v. Washington", "Daubert v. Merrell Dow", "Contacts to experts"),
    ("Chevron v. NRDC", "King v. Burwell", "Deference to the exchanges"),
    ("Celotex v. Catrett", "Ashcroft v. Iqbal", "Summary judgment to plausibility"),
    ("McCulloch v. Maryland", "United States v. Lopez", "Necessary and proper to guns in schools"),
    ("Gibbons v. Ogden", "Gonzales v. Raich", "Steamboats to marijuana"),
    ("Yick Wo v. Hopkins", "Batson v. Kentucky", "Laundries to juries"),
    ("West Virginia v. Barnette", "Masterpiece Cakeshop v. Colorado", "Flag salute to cake"),
    ("Engel v. Vitale", "Employment Division v. Smith", "Prayer to peyote"),
    ("Terry v. Ohio", "Riley v. California", "Stop and frisk to phones"),
    ("Furman v. Georgia", "Roper v. Simmons", "Death penalty, then and now"),
    ("Slaughter-House Cases", "McDonald v. Chicago", "Privileges or immunities"),
    ("Near v. Minnesota", "New York Times v. United States", "Prior restraint"),
    ("Muller v. Oregon", "Craig v. Boren", "Women's hours to beer"),
    ("Ex parte Milligan", "Boumediene v. Bush", "Military tribunals"),
]


def main():
    serve.load()
    found, _ = starters.find_ids()
    by_name = {v[1]: k for k, v in found.items()}
    print("und\tback\tfwd\tstart\ttarget\ttheme")
    for a, b, theme in CANDIDATES:
        ia, ib = by_name.get(a), by_name.get(b)
        if ia is None or ib is None:
            print(f"?\t?\t?\t{a}\t{b}\tmissing {'A' if ia is None else 'B'}")
            continue
        und = serve.bfs_from(ia, "any", 6).get(ib)
        # back-only: from the newer case to the older one
        new, old = (ib, ia) if serve.NODES[ib]["year"] >= serve.NODES[ia]["year"] else (ia, ib)
        back = serve.bfs_from(new, "back", 6).get(old)
        fwd = serve.bfs_from(old, "forward", 6).get(new)
        print(f"{und}\t{back}\t{fwd}\t{a}\t{b}\t{theme}\t{ia}\t{ib}")


if __name__ == "__main__":
    main()
