<!--
DRAFT — put this in your own words before you rely on it.
Every fact here is accurate (dates come from the project's git history), but
interviewers may ask about any of it, so make sure it sounds like you.
This comment is not shown on the website.
-->

MyCarbon began in **January 2025 as my MYP 5 Personal Project**. The goal was
simple: a calculator where you type in how you live and get your carbon
footprint back. It brought together the three things I enjoy most:
environmental science, maths and programming.

The Personal Project ended. The project didn't. I kept coming back to it, and
nearly two years later it has grown from a single number on a screen into a
full tool: it uses India's own electricity data, shows results as an honest
range instead of a falsely precise figure, and plans the changes that would
cut your footprint the most for the money you have.

That last part came from a question the first version couldn't answer: a
number on its own doesn't tell you what to *do*. If you only have a certain
amount to spend, which changes cut the most carbon? It turned out to be a
classic problem in computer science, the **knapsack problem**, and I solved it
with **dynamic programming**, which finds the best combination exactly. I
checked it against a program that tries every possible combination.

The lessons I value most came from two bugs that never caused an error
message. One version told people to carpool, take the metro, cycle *and* buy
an electric car for the same commute, and added up all four savings. In
another, a fuel figure meant per **litre** was being applied per
**kilometre**, so a normal commute came out at 34 tonnes of CO₂ a year. The
code ran perfectly both times. Only the numbers were wrong, and fixing them
made the results look less impressive and much closer to the truth.

I also learned that the data matters as much as the code. On India's
coal-heavy grid, an electric car is only about 30% cleaner than a petrol one,
so the right advice for someone in India isn't the same as for someone in
Europe.

I'm still building it. Next, I want to use real Indian prices for each change,
count the money that changes like solar panels save you, and add flights.
