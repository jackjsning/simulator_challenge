# Built Robotics RC Challenge

## Background
We’ve given you a very basic robot navigation simulator that moves a simulated robot around in a 1D line. Your job is to extend the existing code base’s functionality to enable the robot to navigate on a 2D plane.

## Setup
### Dependencies
Only 2! You'll need to install docker and make.

### Building the container
From the root project directory run `make build_container`. Then you're done! 

## Running the code
From the root project directory:
1. `make redis`: This will start a background redis container on the default port (6379).
2. `make clean_redis`: Stops and removes the redis container.
3. `make shell`: Runs an interactive bash terminal on the container.
4. `make format`: Runs our python code formatter (Black) on the `src` directory. rc_challenge is already formatted by Black is also the formatter we use in our production code base. 
5. `make type_check`: We use Mypy for static type-checking Python's type annotations. Using this command is optional, but it can be helpful for catching type-related bugs. 

From the container's shell terminal (use separate terminals for each command):
1. `python3 src/node/rc_input.py`: Reads keyboard inputs and publishes joystick deflections over the `RC_JS_DEF` pub-sub topic.
2. `python3 src/node/simulator.py`: Maintains the position of the robot. Updates the position based on joystick deflections that it reads from the `RC_JS_DEF` topic. Publishes the current position of the robot over the `ODOMETRY` topic.
3. `python3 src/node/rc_viewer.py`: Reads the robot position from the `ODOMETRY` topic and displays the position.

**These steps should be very quick, let us know if anything isn’t working out of the box.

## Deliverables

1. Design doc (recommended) - Please follow this [template](https://www.industrialempathy.com/posts/design-docs-at-google/). Things to think about as you’re writing the doc:
    * Do your best to infer the intentions of the code base. How was it designed? What are the logical places where you could extend it?
    * Given that this is a (relatively) brief time to spend on a real codebase, it’s fine to make assumptions. Be very specific & clear about your assumptions in your design doc.
    * Please include a system diagram. We like to use Google Slides or LucidChart.
    * Since this is only a day-long project, we expect just a 1-2 page document. If you think it's more clear to document your work in your code as docstrings, that's acceptable as well.
2. Product Requirements:
    * 2D Map internal map representation.
    * New keyboard functionality:
        * Left -> turn left 90 degrees
        * Right -> turn right 90 degrees
        * Up -> move forward
        * Down -> move backward
    * UI: Display the location & orientation however you like. We're not looking for anything fancy. If you want to simply print out the robots position and orientation, that's fine as well.
3. Bonus: show us what you can do! Please also include design decisions in the design doc. Some ideas:
    * Safety monitor: New node that keeps track of the robot’s location and disables keyboard input when you attempt to move outside the map boundary. For this one, be thoughtful about architecture design. In real life, a safety monitor would keep track of multiple safety conditions (pedestrians, collisions, hardware state, etc).
    * GUI display: Improve the UI by implementing a graphical interface.
    * Obstacles: Add the ability for the map to contain obstacles that prevent the movement of the robot upon collision.

## Checkpoints

1. Take a look around the codebase and see how everything works. Keep in mind that even though this seems like an unnecessarily complicated setup for such a simple app, this framework will be the foundation of Built’s future production robot software. Spend about an hour looking around the code before moving onto the next step. Please send questions to the interview slack channel!
2. Spend a few hours playing around with the code, experimenting with new nodes, and making your design doc. 
3. Check in with an engineer and discuss your design doc. Align on implementation steps.
4. Implement! If you feel at this point your goals require more time than you have left, it's okay to decrease the scope of whatever you implement. We are more interested in seeing how much good code/design you can produce in a day than how much functionality you can add with bad code. Let us know if you also want to extend the deadline to the following day. 


## Evaluation
1. **Correctness**: First and foremost, this challenge is about getting something working. 
2. **Understandability**: We prefer that you build a simple solution that is up to code standards than something with more functionality but poor design/code. In the real world, simple solutions pass code review and get merged. Overly complicated solutions with poor design, no matter how functional, don’t (at least, they shouldn’t).
    * For code style, even though there are multiple good ways of writing code, it's important for an entirety of a code base to have *consistent* style. Try to keep the standards that already exist.
    * In concrete terms, we would much rather you implement the basic 2D map really well than a half-baked 2D map w/a half-baked bonus feature.
3. **Communication**: Effective communication is very important. Make sure to talk through the issues that you're thinking about and ask clarifying questions.
    * If you need to put hacks into your code, or you need to move on from a section before you’d like to, just write comments or document in your design doc, explaining why and what you’d like to change if you had more time.
