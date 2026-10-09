# SCOTUS citation graph stats

- SCOTUS clusters (nodes file): 499,548; with at least one mapped opinion: 499,548
- Nodes that appear in at least one SCOTUS->SCOTUS edge: 46,737
- SCOTUS->SCOTUS cluster-level edges: 325,314 (self-cites excluded)
- Mapped clusters with no SCOTUS edges at all (isolated; mostly cert denials/orders): 452,811
- Nodes by decade: 1750s: 1, 1760s: 11, 1770s: 9, 1780s: 97, 1790s: 181, 1800s: 358, 1810s: 492, 1820s: 453, 1830s: 522, 1840s: 433, 1850s: 829, 1860s: 1,128, 1870s: 2,436, 1880s: 2,953, 1890s: 2,880, 1900s: 3,615, 1910s: 4,306, 1920s: 5,993, 1930s: 9,779, 1940s: 14,161, 1950s: 16,080, 1960s: 27,072, 1970s: 40,571, 1980s: 61,525, 1990s: 115,243, 2000s: 95,677, 2010s: 88,738, 2020s: 4,005

## Degree distribution (within the SCOTUS->SCOTUS graph)

| in-degree | nodes | share |
|---|---|---|
| 0 | 14135 | 30.2% |
| 1 | 8937 | 19.1% |
| 2 | 3321 | 7.1% |
| 3-5 | 6010 | 12.9% |
| 6-10 | 5367 | 11.5% |
| 11-20 | 4727 | 10.1% |
| 21-50 | 3402 | 7.3% |
| 51-100 | 685 | 1.5% |
| 101-500 | 150 | 0.3% |
| 501+ | 3 | 0.0% |

| out-degree | nodes | share |
|---|---|---|
| 0 | 8643 | 18.5% |
| 1 | 12373 | 26.5% |
| 2 | 3691 | 7.9% |
| 3-5 | 6945 | 14.9% |
| 6-10 | 5719 | 12.2% |
| 11-20 | 5017 | 10.7% |
| 21-50 | 3655 | 7.8% |
| 51-100 | 622 | 1.3% |
| 101-500 | 72 | 0.2% |
| 501+ | 0 | 0.0% |

Mean in/out degree: 6.96; median in-degree: 2; median out-degree: 2

## Top 40 most-cited SCOTUS cases within the SCOTUS graph (distinct citing clusters)

| rank | cluster_id | case | cited by SCOTUS clusters | cited by opinions, all courts | CL citation_count |
|---|---|---|---|---|---|
| 1 | 109532 | Gregg v. Georgia (428 U.S. 153) | 1197 | 7973 | 7990 |
| 2 | 96405 | United States v. Detroit Timber & Lumber Co. (200 U.S. 321) | 1101 | 1302 | 1302 |
| 3 | 112790 | Martin v. District of Columbia Court of Appeals (506 U.S. 1) | 660 | 804 | 804 |
| 4 | 85272 | M'culloch v. State of Maryland (17 U.S. 316) | 466 | 4230 | 4232 |
| 5 | 137739 | United States v. Booker (543 U.S. 220) | 347 | 23229 | 23233 |
| 6 | 84759 | Marbury v. Madison (5 U.S. 137) | 320 | 6055 | 6054 |
| 7 | 107252 | Miranda v. Arizona (384 U.S. 436) | 317 | 57532 | 58593 |
| 8 | 85412 | Gibbons v. Ogden (22 U.S. 1) | 291 | 2550 | 2550 |
| 9 | 111075 | Theodis Brown v. Herald Co., Inc., Etc (464 U.S. 928) | 288 | 298 | 298 |
| 10 | 111221 | Chevron U. S. A. Inc. v. Natural Resources Defense Council,  (467 U.S. 837) | 281 | 20727 | 20732 |
| 11 | 8954562 | Gideon v. Wainwright (372 U.S. 335) | 278 | 8351 | 8445 |
| 12 | 85330 | Cohens v. Virginia (19 U.S. 264) | 245 | 2085 | 2087 |
| 13 | 102605 | Ashwander v. Tennessee Valley Authority (297 U.S. 288) | 243 | 3156 | 3157 |
| 14 | 91573 | Boyd v. United States (116 U.S. 616) | 242 | 3751 | 3826 |
| 15 | 103012 | Erie Railroad v. Tompkins (304 U.S. 64) | 236 | 18685 | 18682 |
| 16 | 103355 | Cantwell v. Connecticut (310 U.S. 296) | 227 | 3684 | 3684 |
| 17 | 85451 | Osborn v. Bank of United States (22 U.S. 738) | 216 | 1912 | 1912 |
| 18 | 96819 | Ex Parte Young (209 U.S. 123) | 216 | 9820 | 9848 |
| 19 | 106761 | New York Times Co. v. Sullivan (376 U.S. 254) | 212 | 8516 | 8564 |
| 20 | 111170 | Strickland v. Washington (466 U.S. 668) | 204 | 119566 | 124722 |
| 21 | 105221 | Brown v. Board of Education (347 U.S. 483) | 198 | 3795 | 3826 |
| 22 | 103050 | Johnson v. Zerbst (304 U.S. 458) | 195 | 10548 | 10577 |
| 23 | 109380 | Buckley v. Valeo (424 U.S. 1) | 192 | 5060 | 5062 |
| 24 | 105746 | National Ass'n for the Advancement of Colored People v. Alab (357 U.S. 449) | 191 | 2622 | 2622 |
| 25 | 91704 | Yick Wo v. Hopkins (118 U.S. 356) | 191 | 3814 | 3815 |
| 26 | 106285 | Mapp v. Ohio (367 U.S. 643) | 189 | 9104 | 9128 |
| 27 | 105547 | Roth v. United States (354 U.S. 476) | 187 | 3264 | 3266 |
| 28 | 108111 | In Re WINSHIP (397 U.S. 358) | 184 | 11668 | 11776 |
| 29 | 107729 | Terry v. Ohio (392 U.S. 1) | 183 | 37893 | 38187 |
| 30 | 103870 | West Virginia State Board of Education v. Barnette (319 U.S. 624) | 183 | 2490 | 2491 |
| 31 | 106514 | National Ass'n for the Advancement of Colored People v. Butt (371 U.S. 415) | 182 | 3092 | 3093 |
| 32 | 106366 | Baker v. Carr (369 U.S. 186) | 180 | 6203 | 6207 |
| 33 | 106850 | Reynolds v. Sims (377 U.S. 533) | 172 | 3703 | 3706 |
| 34 | 108263 | Younger v. Harris (401 U.S. 37) | 170 | 15151 | 15144 |
| 35 | 1236300 | Powell v. Alabama (287 U.S. 45) | 169 | 4994 | 5000 |
| 36 | 108838 | Miller v. California (413 U.S. 15) | 167 | 3043 | 3046 |
| 37 | 108605 | Furman v. Georgia (408 U.S. 238) | 166 | 5040 | 5070 |
| 38 | 103347 | Thornhill v. Alabama (310 U.S. 88) | 165 | 2326 | 2352 |
| 39 | 107564 | Katz v. United States (389 U.S. 347) | 164 | 13203 | 13392 |
| 40 | 103243 | Schneider v. State (Town of Irvington) (308 U.S. 147) | 163 | 1687 | 1688 |

## Top 40 most-cited SCOTUS cases across all courts (citing opinions in the full citation map)

| rank | cluster_id | case | citing opinions, all courts | SCOTUS in-degree | CL citation_count |
|---|---|---|---|---|---|
| 1 | 145875 | Ashcroft v. Iqbal (556 U.S. 662) | 159004 | 40 | 159280 |
| 2 | 145730 | Bell Atlantic Corp. v. Twombly (550 U.S. 544) | 155785 | 27 | 155999 |
| 3 | 111719 | Anderson v. Liberty Lobby, Inc. (477 U.S. 242) | 138555 | 43 | 138478 |
| 4 | 111722 | Celotex Corp. v. Catrett, Administratrix of the Estate of Ca (477 U.S. 317) | 122464 | 20 | 122401 |
| 5 | 111170 | Strickland v. Washington (466 U.S. 668) | 119566 | 204 | 124722 |
| 6 | 107423 | Anders v. California (386 U.S. 738) | 87895 | 34 | 88538 |
| 7 | 110138 | Jackson v. Virginia (443 U.S. 307) | 79770 | 82 | 79856 |
| 8 | 111620 | Matsushita Electric Industrial Co., Ltd. v. Zenith Radio Cor (475 U.S. 574) | 60100 | 31 | 60076 |
| 9 | 107252 | Miranda v. Arizona (384 U.S. 436) | 57532 | 317 | 58593 |
| 10 | 109881 | Monell v. New York City Dept. of Social Servs. (436 U.S. 658) | 43217 | 118 | 43234 |
| 11 | 118359 | Slack v. McDaniel (529 U.S. 473) | 42378 | 43 | 42370 |
| 12 | 108786 | McDonnell Douglas Corp. v. Green (411 U.S. 792) | 39054 | 81 | 39101 |
| 13 | 107729 | Terry v. Ohio (392 U.S. 1) | 37893 | 183 | 38187 |
| 14 | 145722 | Erickson v. Pardus (551 U.S. 89) | 37102 | 4 | 37078 |
| 15 | 106598 | Brady v. Maryland (373 U.S. 83) | 33869 | 133 | 34263 |
| 16 | 111545 | Thomas v. Arn (474 U.S. 140) | 31110 | 11 | 31096 |
| 17 | 105573 | Conley v. Gibson (355 U.S. 41) | 30863 | 63 | 30878 |
| 18 | 1087956 | Farmer v. Brennan (511 U.S. 825) | 29650 | 41 | 29634 |
| 19 | 109561 | Estelle v. Gamble (429 U.S. 97) | 29279 | 72 | 29267 |
| 20 | 122258 | Miller-El v. Cockrell (537 U.S. 322) | 28021 | 52 | 28021 |
| 21 | 118381 | Apprendi v. New Jersey (530 U.S. 466) | 27646 | 122 | 28488 |
| 22 | 108432 | Haines v. Kerner (404 U.S. 519) | 27367 | 27 | 27353 |
| 23 | 112747 | Lujan v. Defenders of Wildlife (504 U.S. 555) | 25592 | 129 | 25613 |
| 24 | 112254 | Neitzke v. Williams (490 U.S. 319) | 23701 | 16 | 23688 |
| 25 | 108333 | Richardson v. Perales (402 U.S. 389) | 23585 | 22 | 23572 |
| 26 | 137739 | United States v. Booker (543 U.S. 220) | 23229 | 347 | 23233 |
| 27 | 107359 | Chapman v. California (386 U.S. 18) | 23078 | 160 | 23187 |
| 28 | 110763 | Harlow v. Fitzgerald (457 U.S. 800) | 23046 | 92 | 23235 |
| 29 | 106383 | Coppedge v. United States (369 U.S. 438) | 22759 | 23 | 22749 |
| 30 | 112903 | Daubert v. Merrell Dow Pharmaceuticals, Inc. (509 U.S. 579) | 21460 | 20 | 21796 |
| 31 | 145843 | Gall v. United States (552 U.S. 38) | 20735 | 34 | 20734 |
| 32 | 111221 | Chevron U. S. A. Inc. v. Natural Resources Defense Council,  (467 U.S. 837) | 20727 | 281 | 20732 |
| 33 | 104200 | International Shoe Co. v. Washington (326 U.S. 310) | 18778 | 69 | 18877 |
| 34 | 103012 | Erie Railroad v. Tompkins (304 U.S. 64) | 18685 | 236 | 18682 |
| 35 | 109382 | Mathews v. Eldridge (424 U.S. 319) | 18673 | 135 | 18843 |
| 36 | 108375 | Bivens v. Six Unknown Named Agents of Federal Bureau of Narc (403 U.S. 388) | 18558 | 149 | 18569 |
| 37 | 106497 | Foman v. Davis (371 U.S. 178) | 18125 | 27 | 18137 |
| 38 | 112116 | West v. Atkins (487 U.S. 42) | 17777 | 10 | 17779 |
| 39 | 110929 | Hensley v. Eckerhart (461 U.S. 424) | 17556 | 49 | 17749 |
| 40 | 112257 | Graham v. Connor (490 U.S. 386) | 17042 | 52 | 17036 |

## Connectivity

- Weakly connected components: 2,283; largest has 41,952 nodes (89.8% of non-isolated nodes); next sizes: [18, 18, 9, 9, 7]

## Path lengths (undirected, 2000 random pairs, seed 1)

### Shortest path lengths (full graph)

reachable pairs: 1568/2000; mean 4.54, median 4, max 9

| path length | pairs | share |
|---|---|---|
| 1 | 1 | 0.1% |
| 2 | 19 | 0.9% |
| 3 | 204 | 10.2% |
| 4 | 567 | 28.4% |
| 5 | 525 | 26.2% |
| 6 | 195 | 9.8% |
| 7 | 50 | 2.5% |
| 8 | 6 | 0.3% |
| 9 | 1 | 0.1% |
| unreachable | 432 | 21.6% |

After removing top 20 hubs: 46,717 nodes, 316,884 edges, largest component 39,886 (85.4%)

### Shortest path lengths (top 20 hubs removed)

reachable pairs: 1468/2000; mean 4.55, median 5, max 8

| path length | pairs | share |
|---|---|---|
| 1 | 2 | 0.1% |
| 2 | 14 | 0.7% |
| 3 | 173 | 8.7% |
| 4 | 528 | 26.4% |
| 5 | 528 | 26.4% |
| 6 | 187 | 9.3% |
| 7 | 33 | 1.6% |
| 8 | 3 | 0.1% |
| unreachable | 532 | 26.6% |

After removing top 100 hubs: 46,637 nodes, 302,490 edges, largest component 39,557 (84.8%)

### Shortest path lengths (top 100 hubs removed)

reachable pairs: 1417/2000; mean 4.58, median 5, max 8

| path length | pairs | share |
|---|---|---|
| 1 | 3 | 0.1% |
| 2 | 16 | 0.8% |
| 3 | 145 | 7.2% |
| 4 | 532 | 26.6% |
| 5 | 485 | 24.2% |
| 6 | 198 | 9.9% |
| 7 | 31 | 1.6% |
| 8 | 7 | 0.3% |
| unreachable | 583 | 29.1% |

## Sanity check: well-known cases

| case | cite | cluster_id | name in CL | SCOTUS in-degree | SCOTUS out-degree | in-degree all courts |
|---|---|---|---|---|---|---|
| Twombly | 550 U.S. 544 | 145730 | Bell Atlantic Corp. v. Twombly | 27 | 53 | 155785 |
| Iqbal | 556 U.S. 662 | 145875 | Ashcroft v. Iqbal | 40 | 33 | 159004 |
| Celotex | 477 U.S. 317 | 111722 | Celotex Corp. v. Catrett, Administratrix of the Es | 20 | 12 | 122464 |
| Liberty Lobby | 477 U.S. 242 | 111719 | Anderson v. Liberty Lobby, Inc. | 43 | 28 | 138555 |
| Chevron | 467 U.S. 837 | 111221 | Chevron U. S. A. Inc. v. Natural Resources Defense | 281 | 43 | 20727 |
| Erie | 304 U.S. 64 | 103012 | Erie Railroad v. Tompkins | 236 | 53 | 18685 |
| Marbury | 5 U.S. 137 | 84759 | Marbury v. Madison | 320 | 0 | 6055 |
| Brown v. Board | 347 U.S. 483 | 105221 | Brown v. Board of Education | 198 | 15 | 3795 |
