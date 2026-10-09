<!--
DRAFT — rewrite this in your own words before you publish it.
It will be read as yours, and interviewers may ask about anything in it.
Everything below is accurate to the project; the phrasing is only a starting point.
This comment is not shown on the website.
-->

I built MyCarbon because it brings together the three things I enjoy most:
environmental science, maths and programming. It started as a simple
calculator: type in how you live, get a number back. But a number on its own
doesn't tell you what to do next, so I set myself a harder question: if you
only have a certain amount to spend, which changes cut the most carbon?

That question turned out to be a classic problem in computer science, the
**knapsack problem**: choosing the most valuable set of items that fit into a
bag of limited size. I solved it with **dynamic programming**, which finds the
best combination exactly instead of trying all of them one by one, and I
checked it against a program that does try every combination.

The most useful lessons came from two bugs that never caused an error message.
The first version told people to carpool, take the metro, cycle *and* buy an
electric car for the same commute, then added up all four savings. The maths
was right, but the model was wrong. In another version, a fuel figure meant
per **litre** was being applied per **kilometre**, so a normal commute came out
at 34 tonnes of CO₂ a year. Both times, fixing the bug made the result look
less impressive, and much closer to the truth.

I also learned that the data matters as much as the code. On India's
coal-heavy electricity grid, an electric car is only about 30% cleaner than a
petrol one, so the best advice for an Indian user isn't the same as for someone
in Europe.

Next, I want to replace the estimated costs with real Indian prices, account
for changes that pay for themselves, and add flights, which the calculator
doesn't count yet.
