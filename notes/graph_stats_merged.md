# SCOTUS citation graph stats

- SCOTUS clusters (nodes file): 496,313; with at least one mapped opinion: 496,313
- Nodes that appear in at least one SCOTUS->SCOTUS edge: 43,155
- SCOTUS->SCOTUS cluster-level edges: 304,448 (self-cites excluded)
- Mapped clusters with no SCOTUS edges at all (isolated; mostly cert denials/orders): 453,158
- Nodes by decade: 1750s: 1, 1760s: 11, 1770s: 9, 1780s: 97, 1790s: 163, 1800s: 300, 1810s: 423, 1820s: 436, 1830s: 494, 1840s: 417, 1850s: 818, 1860s: 1,121, 1870s: 2,409, 1880s: 2,898, 1890s: 2,745, 1900s: 3,542, 1910s: 4,253, 1920s: 5,923, 1930s: 9,705, 1940s: 14,100, 1950s: 15,986, 1960s: 26,848, 1970s: 40,452, 1980s: 61,041, 1990s: 114,693, 2000s: 95,501, 2010s: 88,180, 2020s: 3,747

## Degree distribution (within the SCOTUS->SCOTUS graph)

| in-degree | nodes | share |
|---|---|---|
| 0 | 11900 | 27.6% |
| 1 | 8112 | 18.8% |
| 2 | 3219 | 7.5% |
| 3-5 | 6047 | 14.0% |
| 6-10 | 5385 | 12.5% |
| 11-20 | 4633 | 10.7% |
| 21-50 | 3116 | 7.2% |
| 51-100 | 616 | 1.4% |
| 101-500 | 124 | 0.3% |
| 501+ | 3 | 0.0% |

| out-degree | nodes | share |
|---|---|---|
| 0 | 7973 | 18.5% |
| 1 | 10518 | 24.4% |
| 2 | 3512 | 8.1% |
| 3-5 | 6752 | 15.6% |
| 6-10 | 5559 | 12.9% |
| 11-20 | 4820 | 11.2% |
| 21-50 | 3406 | 7.9% |
| 51-100 | 549 | 1.3% |
| 101-500 | 66 | 0.2% |
| 501+ | 0 | 0.0% |

Mean in/out degree: 7.05; median in-degree: 2; median out-degree: 2

## Top 40 most-cited SCOTUS cases within the SCOTUS graph (distinct citing clusters)

| rank | cluster_id | case | cited by SCOTUS clusters | cited by opinions, all courts | CL citation_count |
|---|---|---|---|---|---|
| 1 | 96405 | United States v. Detroit Timber & Lumber Co. (200 U.S. 321) | 990 | 1302 | 1302 |
| 2 | 109532 | Gregg v. Georgia (428 U.S. 153) | 901 | 7973 | 7990 |
| 3 | 112790 | Martin v. District of Columbia Court of Appeals (506 U.S. 1) | 604 | 804 | 804 |
| 4 | 85272 | M'culloch v. State of Maryland (17 U.S. 316) | 428 | 4230 | 4232 |
| 5 | 107252 | Miranda v. Arizona (384 U.S. 436) | 297 | 57532 | 58593 |
| 6 | 137739 | United States v. Booker (543 U.S. 220) | 295 | 23229 | 23233 |
| 7 | 84759 | Marbury v. Madison (5 U.S. 137) | 284 | 6055 | 6054 |
| 8 | 85412 | Gibbons v. Ogden (22 U.S. 1) | 273 | 2550 | 2550 |
| 9 | 111221 | Chevron U. S. A. Inc. v. Natural Resources Defense Council,  (467 U.S. 837) | 263 | 20727 | 20732 |
| 10 | 8954562 | Gideon v. Wainwright (372 U.S. 335) | 252 | 15597 | 15776 |
| 11 | 91573 | Boyd v. United States (116 U.S. 616) | 237 | 3751 | 3826 |
| 12 | 102605 | Ashwander v. Tennessee Valley Authority (297 U.S. 288) | 227 | 3156 | 3157 |
| 13 | 103012 | Erie Railroad v. Tompkins (304 U.S. 64) | 223 | 18685 | 18682 |
| 14 | 85330 | Cohens v. Virginia (19 U.S. 264) | 222 | 2089 | 2091 |
| 15 | 103355 | Cantwell v. Connecticut (310 U.S. 296) | 217 | 3684 | 3684 |
| 16 | 85451 | Osborn v. Bank of United States (22 U.S. 738) | 203 | 1912 | 1912 |
| 17 | 106761 | New York Times Co. v. Sullivan (376 U.S. 254) | 201 | 8516 | 8564 |
| 18 | 96819 | Ex Parte Young (209 U.S. 123) | 195 | 9820 | 9848 |
| 19 | 105221 | Brown v. Board of Education (347 U.S. 483) | 191 | 3795 | 3826 |
| 20 | 111170 | Strickland v. Washington (466 U.S. 668) | 185 | 119566 | 124722 |
| 21 | 103050 | Johnson v. Zerbst (304 U.S. 458) | 185 | 10548 | 10577 |
| 22 | 91704 | Yick Wo v. Hopkins (118 U.S. 356) | 184 | 3814 | 3815 |
| 23 | 105746 | National Ass'n for the Advancement of Colored People v. Alab (357 U.S. 449) | 183 | 2622 | 2622 |
| 24 | 106514 | National Ass'n for the Advancement of Colored People v. Butt (371 U.S. 415) | 179 | 3092 | 3093 |
| 25 | 111075 | Theodis Brown v. Herald Co., Inc., Etc (464 U.S. 928) | 179 | 298 | 298 |
| 26 | 105547 | Roth v. United States (354 U.S. 476) | 178 | 3264 | 3266 |
| 27 | 106285 | Mapp v. Ohio (367 U.S. 643) | 178 | 9104 | 9128 |
| 28 | 109380 | Buckley v. Valeo (424 U.S. 1) | 176 | 5060 | 5062 |
| 29 | 107729 | Terry v. Ohio (392 U.S. 1) | 174 | 37893 | 38187 |
| 30 | 106366 | Baker v. Carr (369 U.S. 186) | 171 | 6203 | 6207 |
| 31 | 103870 | West Virginia State Board of Education v. Barnette (319 U.S. 624) | 169 | 2490 | 2491 |
| 32 | 108111 | In Re WINSHIP (397 U.S. 358) | 169 | 11668 | 11776 |
| 33 | 106850 | Reynolds v. Sims (377 U.S. 533) | 168 | 3703 | 3706 |
| 34 | 1236300 | Powell v. Alabama (287 U.S. 45) | 163 | 4994 | 5000 |
| 35 | 108838 | Miller v. California (413 U.S. 15) | 162 | 3043 | 3046 |
| 36 | 108263 | Younger v. Harris (401 U.S. 37) | 160 | 15151 | 15144 |
| 37 | 103347 | Thornhill v. Alabama (310 U.S. 88) | 159 | 2326 | 2352 |
| 38 | 108605 | Furman v. Georgia (408 U.S. 238) | 159 | 5040 | 5070 |
| 39 | 107564 | Katz v. United States (389 U.S. 347) | 158 | 13203 | 13392 |
| 40 | 103243 | Schneider v. State (Town of Irvington) (308 U.S. 147) | 157 | 1687 | 1688 |

## Top 40 most-cited SCOTUS cases across all courts (citing opinions in the full citation map)

| rank | cluster_id | case | citing opinions, all courts | SCOTUS in-degree | CL citation_count |
|---|---|---|---|---|---|
| 1 | 145875 | Ashcroft v. Iqbal (556 U.S. 662) | 159004 | 30 | 159280 |
| 2 | 145730 | Bell Atlantic Corp. v. Twombly (550 U.S. 544) | 155785 | 21 | 155999 |
| 3 | 111719 | Anderson v. Liberty Lobby, Inc. (477 U.S. 242) | 138555 | 41 | 138478 |
| 4 | 111722 | Celotex Corp. v. Catrett, Administratrix of the Estate of Ca (477 U.S. 317) | 122464 | 20 | 122401 |
| 5 | 111170 | Strickland v. Washington (466 U.S. 668) | 119566 | 185 | 124722 |
| 6 | 107423 | Anders v. California (386 U.S. 738) | 87895 | 34 | 88538 |
| 7 | 110138 | Jackson v. Virginia (443 U.S. 307) | 79770 | 76 | 79856 |
| 8 | 111620 | Matsushita Electric Industrial Co., Ltd. v. Zenith Radio Cor (475 U.S. 574) | 60100 | 28 | 60076 |
| 9 | 107252 | Miranda v. Arizona (384 U.S. 436) | 57532 | 297 | 58593 |
| 10 | 109881 | Monell v. New York City Dept. of Social Servs. (436 U.S. 658) | 43217 | 110 | 43234 |
| 11 | 118359 | Slack v. McDaniel (529 U.S. 473) | 42378 | 35 | 42370 |
| 12 | 108786 | McDonnell Douglas Corp. v. Green (411 U.S. 792) | 39054 | 76 | 39101 |
| 13 | 107729 | Terry v. Ohio (392 U.S. 1) | 37893 | 174 | 38187 |
| 14 | 145722 | Erickson v. Pardus (551 U.S. 89) | 37102 | 4 | 37078 |
| 15 | 106598 | Brady v. Maryland (373 U.S. 83) | 33869 | 124 | 34263 |
| 16 | 111545 | Thomas v. Arn (474 U.S. 140) | 31110 | 9 | 31096 |
| 17 | 105573 | Conley v. Gibson (355 U.S. 41) | 30863 | 62 | 30878 |
| 18 | 1087956 | Farmer v. Brennan (511 U.S. 825) | 29650 | 37 | 29634 |
| 19 | 109561 | Estelle v. Gamble (429 U.S. 97) | 29279 | 67 | 29267 |
| 20 | 122258 | Miller-El v. Cockrell (537 U.S. 322) | 28021 | 44 | 28021 |
| 21 | 118381 | Apprendi v. New Jersey (530 U.S. 466) | 27646 | 107 | 28488 |
| 22 | 108432 | Haines v. Kerner (404 U.S. 519) | 27367 | 27 | 27353 |
| 23 | 112747 | Lujan v. Defenders of Wildlife (504 U.S. 555) | 25592 | 102 | 25613 |
| 24 | 112254 | Neitzke v. Williams (490 U.S. 319) | 23701 | 13 | 23688 |
| 25 | 108333 | Richardson v. Perales (402 U.S. 389) | 23585 | 18 | 23572 |
| 26 | 137739 | United States v. Booker (543 U.S. 220) | 23229 | 295 | 23233 |
| 27 | 107359 | Chapman v. California (386 U.S. 18) | 23078 | 152 | 23187 |
| 28 | 110763 | Harlow v. Fitzgerald (457 U.S. 800) | 23046 | 88 | 23235 |
| 29 | 106383 | Coppedge v. United States (369 U.S. 438) | 22759 | 21 | 22749 |
| 30 | 112903 | Daubert v. Merrell Dow Pharmaceuticals, Inc. (509 U.S. 579) | 21460 | 17 | 21796 |
| 31 | 145843 | Gall v. United States (552 U.S. 38) | 20735 | 25 | 20734 |
| 32 | 111221 | Chevron U. S. A. Inc. v. Natural Resources Defense Council,  (467 U.S. 837) | 20727 | 263 | 20732 |
| 33 | 104200 | International Shoe Co. v. Washington (326 U.S. 310) | 18778 | 64 | 18877 |
| 34 | 103012 | Erie Railroad v. Tompkins (304 U.S. 64) | 18685 | 223 | 18682 |
| 35 | 109382 | Mathews v. Eldridge (424 U.S. 319) | 18673 | 130 | 18843 |
| 36 | 108375 | Bivens v. Six Unknown Named Agents of Federal Bureau of Narc (403 U.S. 388) | 18558 | 140 | 18569 |
| 37 | 106497 | Foman v. Davis (371 U.S. 178) | 18125 | 21 | 18137 |
| 38 | 112116 | West v. Atkins (487 U.S. 42) | 17777 | 9 | 17779 |
| 39 | 110929 | Hensley v. Eckerhart (461 U.S. 424) | 17556 | 45 | 17749 |
| 40 | 112257 | Graham v. Connor (490 U.S. 386) | 17042 | 48 | 17036 |

## Connectivity

- Weakly connected components: 1,695; largest has 39,497 nodes (91.5% of non-isolated nodes); next sizes: [54, 18, 16, 7, 7]

## Path lengths (undirected, 2000 random pairs, seed 1)

### Shortest path lengths (full graph)

reachable pairs: 1638/2000; mean 4.50, median 4, max 9

| path length | pairs | share |
|---|---|---|
| 1 | 1 | 0.1% |
| 2 | 24 | 1.2% |
| 3 | 221 | 11.1% |
| 4 | 615 | 30.8% |
| 5 | 527 | 26.4% |
| 6 | 194 | 9.7% |
| 7 | 50 | 2.5% |
| 8 | 5 | 0.2% |
| 9 | 1 | 0.1% |
| unreachable | 362 | 18.1% |

After removing top 20 hubs: 43,135 nodes, 296,966 edges, largest component 38,069 (88.3%)

### Shortest path lengths (top 20 hubs removed)

reachable pairs: 1539/2000; mean 4.51, median 4, max 8

| path length | pairs | share |
|---|---|---|
| 1 | 2 | 0.1% |
| 2 | 16 | 0.8% |
| 3 | 192 | 9.6% |
| 4 | 580 | 29.0% |
| 5 | 526 | 26.3% |
| 6 | 183 | 9.2% |
| 7 | 36 | 1.8% |
| 8 | 4 | 0.2% |
| unreachable | 461 | 23.1% |

After removing top 100 hubs: 43,055 nodes, 283,147 edges, largest component 37,640 (87.4%)

### Shortest path lengths (top 100 hubs removed)

reachable pairs: 1545/2000; mean 4.59, median 5, max 9

| path length | pairs | share |
|---|---|---|
| 2 | 14 | 0.7% |
| 3 | 162 | 8.1% |
| 4 | 564 | 28.2% |
| 5 | 567 | 28.4% |
| 6 | 193 | 9.7% |
| 7 | 39 | 1.9% |
| 8 | 5 | 0.2% |
| 9 | 1 | 0.1% |
| unreachable | 455 | 22.8% |

## Sanity check: well-known cases

| case | cite | cluster_id | name in CL | SCOTUS in-degree | SCOTUS out-degree | in-degree all courts |
|---|---|---|---|---|---|---|
| Twombly | 550 U.S. 544 | 145730 | Bell Atlantic Corp. v. Twombly | 21 | 52 | 155785 |
| Iqbal | 556 U.S. 662 | 145875 | Ashcroft v. Iqbal | 30 | 33 | 159004 |
| Celotex | 477 U.S. 317 | 111722 | Celotex Corp. v. Catrett, Administratrix of the Es | 20 | 11 | 122464 |
| Liberty Lobby | 477 U.S. 242 | 111719 | Anderson v. Liberty Lobby, Inc. | 41 | 27 | 138555 |
| Chevron | 467 U.S. 837 | 111221 | Chevron U. S. A. Inc. v. Natural Resources Defense | 263 | 43 | 20727 |
| Erie | 304 U.S. 64 | 103012 | Erie Railroad v. Tompkins | 223 | 53 | 18685 |
| Marbury | 5 U.S. 137 | 84759 | Marbury v. Madison | 284 | 0 | 6055 |
| Brown v. Board | 347 U.S. 483 | 105221 | Brown v. Board of Education | 191 | 15 | 3795 |
