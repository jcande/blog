Title: But can DOOM run it?
Date: 2021-10-22 22:18
Category: Programming Satan's Computer
Tags: programming; esoteric
Slug: doom
Authors: Jared Candelaria
TwitterName: @jsc29a
Summary: A half-adder implemented in classic DOOM demonstrating Turing-completeness.

DOOM (the 1993 DOS game) is Turing-complete. That means you can run DOOM on DOOM. Keep reading for implementation details.

[TOC]

# Background
Before diving into the construction, I'll give some context. If you have a background in programming then you can skip over the refresher that attempts to summarize the concept of Turing-completeness.

## What is Turing-completeness?
Ok so some random video game is universal or Turing-complete or programmable. What? This is basically nerd-talk for "you can implement a computer in the game". But there are some caveats because if the player has to do "too much" then it's not as exciting.

Essentially we're looking for something "inevitable". There are a lot of formulations of Turing machines but you can think of them as little machines that run autonomously, take input only when you start them up, and give their output when they finish running. Well, assuming they finish. What we mean by "run" is act on some sequence of instructions. There are more technical aspects but that gives a good intuition for the idea. And believe it or not, any machine capable of doing this is in principle capable of calculating anything humans can imagine. I'm being blunt and these things are nuanced; let's just agree to not nitpick with the Church-Turing thesis for now.

Computation is deceptively simple. I'm going to skip over the mystic and philosophical aspects and boil it down into a concrete task: is this system capable of simulating a NAND gate? If the answer is "yes", then we have a computer. For our intents and purposes, it is literally the same as any other computer. Also, for reference, a NAND gate takes two input signals and returns false if and only if both signals are true.

But your computer likely has a video card, a storage device of some sort, and a bunch of memory, not to mention a network card or two, USB interfaces, etc. And that's true but not relevant for our discussion. If you squint, those things can be built out of NAND gates and if not the NAND-gate-components are "simply" transmitting a signal to something that vibrates a membrane, excites a cell, or something independent from the task that occupies a Turing machine. Now in practice real devices are more than just NAND gates and the IO devices are insanely complicated. But real life is always complicated and besides, just write a simulator!

## DOOM Map Primitives
Now that we have an objective, we'll need to understand what we're working with. Full disclosure here, I'm not going to exhaustively enumerate features of the DOOM engine and will instead focus only on aspects relevant to the final result. Similarly, the DOOM community has come up with an incredibly rich and extensive set of techniques (e.g., DeHackEd, compatibility levels, etc) to enhance the player's experience but we'll ignore all that. If you're curious then hit me up and we can chat about it. Anyway, the DOOM engine essentially loads a map and then simulates what happens to it given a series of user-inputs. That map basically provides textures, and geometry in the form of vertices, lines, and sectors (polygon composed of lines) with corresponding metadata (e.g., ceiling height).

You've probably seen moving floors, opening doors, and flashing lights, so how is that done? That's where the "corresponding metadata" comes in. To paint you a picture, you've got two rooms connected by a narrow hallway. When the player runs from one room to the other, they must necessarily cross a line in the hallway. This line, which the engine refers to as a linedef can have an action associated with it. These actions are responsible for dynamic lighting effects, lifts, doors, etc. For some effects a separate "tag" is required to transmit the action to any objects identified with the tag. Essentially you've got a single action per linedef but that single action can perform its effect on multiple objects (well, up to 8 per game tic). Now true doom-heads will talk about linedef skips or that there are switches and doors which are distinct from linedefs but that is beyond the scope of this article.

One important thing to mention here, it is not only the player that can trigger these actions. The monsters can also. Monsters are capable of opening doors, using teleporters, and activating lifts. The crucial distinction, however, is that monster-available actions are extraordinarily impoverished compared with player-available actions. The previously mentioned list is exhaustive.

To summarize, when a monster crosses a line on a map certain actions can be triggered. The relevant actions are: activating a lift, and teleporting.

# Synthesis: DOOMHDL
With the primitives at our disposal enumerated, we must now weave them into something useful. A good first step is to survey known [Turing-complete systems](https://en.wikipedia.org/wiki/Model_of_computation) and estimate which would be easiest to simulate given our building blocks. If you think of the triggers DOOM provides as rough kinds of boolean activations we get most of the way there. The big issue is how to "sense" these activations? We'll need to feed the outputs back as inputs to the next phase of operation. If we cleave the simulation into yin-like monsters roving the world and yang-esque triggers reshaping rovable-space, then the fog begins to lift. We can have a monster walk over a trigger which lowers a lift. The impacted lift will then allow a second monster to walk over yet more triggers.

But there's still a problem. In DOOM, monsters chase after the player but only after they've woken up. Luckily this is a minor inconvenience and the workaround is spawning all circuit-simulating monsters where they can see the player causing them to run forwards. We'll place a teleporter right in front of them and they'll find themselves locked away in a circuit of our devising spinning a hamster wheel for our benefit. Forever. Just make sure the circuit is placed where the player will always be a specific direction (e.g., south) so they'll forever keep trying to run in that direction.

Now let's implement some gates.

## OR
An OR gate takes two inputs and is true if either is true. We can map this onto a lift that can be lowered in two ways. From inside DOOM, each one of these ways will correspond with a distinct linedef which translates exactly to the OR gates' input signals.

You may also be concerned with what DOOM will do to a lift if you activate it twice. Very keen observation! To be brief, DOOM does NOT keep a queue of triggers and any active trigger is blocking. This means that for the duration of the trigger, all other activations are silently ignored. This works out nicely in our favor.

<center>
![An OR gate implemented in DOOM]({filename}/images/doom-OR.png)
</center>

Pictured above is our implementation of an OR gate. The top two alcoves have triggers that both lower a thin green sector which is blocking a monster's path. Two giant yellow arrows illustrate this linkage. Further along the monster's path is a teleporter that transports the monster back to its initial spawn point which is illustrated by a dotted green arrow. Don't worry if the teleporter is close enough to the gate that the monster runs through it multiple times, due to the behavior of how DOOM activates lifts it won't double-activate anything. The final aspect to observe in the image is the gray line between the green-sector and the teleporter. This tiny linedef represents the output of the gate.

## AND

An AND gate takes two inputs and is only true if BOTH inputs are true. We can implement this with two distinct lifts: the monster can only pass if they're both lowered.

<center>
![An AND gate implemented in DOOM]({filename}/images/doom-AND.png)
</center>

The only difference between this and the OR gate is that each signal triggers a distint sector. Every other aspect from the teleport to the gate output is the same.

## NOT
A NOT gate takes only one input and inverts it: true becomes false and false becomes true. Sounds simple enough until you go to implement it. Since our schema treats demons as signals, how do we materialize one from the aether in the false case? Our previous approach to have walls that lower to enable passage won't do. Instead we can have floors that become trenches when set which prevent passage.

<center>
![A NOT gate implemented in DOOM]({filename}/images/doom-NOT.png)
</center>

This has all the components of the OR gate: the monster, the gate itself, the output linedef, and the teleporter. But you'll also notice something new, a small notch on the left side of the gate. This controls the depth of our trench (remember, lifts in DOOM descend to the lowest adjoining sector height). In this way, we can have the gate at the normal floor height by default (i.e., the false case) but descend when set (i.e., true) to prevent movement.

## REPEATER

This isn't a complicated gate and is only "necessary" because I got anxious and over-thought the problem. You can think of it as the identity gate, meaning it repeats its input: true -> true, false -> false. I got concerned about timing and instead of thinking more just decided to make sure everything took a fixed-amount of time. Now I don't have to deal with possible propogation delays. Aside from all of those timing bugs...

## Misc Engineering Notes
You likely noticed the thin sectors in the images and wonder what function they serve. As the monsters are constantly moving, if they block the lift's path then it won't close. This can cause annoying timing issues. The chosen monster (the pinky demon) is large, however. We can use thin sectors as effective barriers in an attempt to add robustness to the circuits because the monster won't stand on the thin sectors alone, they must be touching walkable floor.

Another aspect of the thin sectors is to control the lifts. DOOM will lower a lift to the lowest neighboring sector. This is employed in the NOT gate.

You may be concerned about timing. And that is an excellent concern. Sure the gates work well enough but how do you string them together? If you just link them together then they'll always be active which can cause problems for two reasons: 1) the monsters increase their chances of standing on a gate when it should be de-activating, and 2) you can't turn the circuit off!

These problems can be addressed by introducing a clock signal. The clock will then be responsible for coarsely choosing which gate is active. This can be implemented by placing the gate-monster up on an island that is only lowered by the clock. The rest of the gates are the same as before. In the above images, this corresponds to the circle texture (think: clock face) on the monster island. If the inputs to the gate are present before the clock activates the gate, then the gates will be certain to transmit their proper output correctly.

And this is the big caveat around the CLK signal. The input signals __must__ have arrived before the clock activates the gate. For the AND and OR gates this isn't really too big of a concern but this is critical for the NOT gate. I spent a ton of time trying to figure out why the circuit worked the first try and only every other subsequent attempt. The problem was that the monster would be lowered and cross the gate before it turned into a trench. Due to timing considerations, the CLK path is spaced such that each phase should only be triggered after the previous phase has completed. There are probably a lot of optimizations around this but this approach worked for me.

# Demonstration: Half-Adder
Now that we have some convenient building blocks, we'll need to actual construct something. The obvious choice would be a NAND gate. And while that is sensible, it feels a bit too simple. A more dramatic demonstration could be a simple CPU but that it time consuming. Instead I opt for something that is only slightly more interesting than a NAND gate: [a half-adder](https://en.wikipedia.org/wiki/Adder_(electronics)#Half_adder). This circuit essentially adds two bits together outputting the sum (mod 2) and the carry. To be concrete, it has 4 possible inputs, and 3 possible outputs.

Traditionally, it looks like this:
<center>
![A traditional half-adder circuit]({filename}/images/doom-half-adder-circuit.png)<br />
[Image taken from https://electronics.stackexchange.com/a/166634](https://electronics.stackexchange.com/a/166634)
</center>

In DOOM, it looks like this:
<center>
![A non-traditional half-adder circuit]({filename}/images/doom-half-adder-map.png)
</center>

And here's a video of it in action:
<center><iframe width="560" height="315" src="https://www.youtube.com/embed/qB9R3L5FZ3Q" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe></center>

## Download
In case you want to play around with the map, you can download it [here]({filename}/data/half-adder.zip). You'll likely want to open it in a doom level editor. I used [Doom Builder](http://doombuilder.com/) to make it.

# Limitations
As the DOOM engine was not designed to be an interpreter, there are some constraints on our programs written against it. The biggest one is how large our programs can be. Since each gate uses at least one tag, we can use this as a metric to derive an upper-bound on the size of a program. As the DOOM engine uses 16-bit tags, this means we can have, at most, 65535 gates. This is not a particularly large number. We may be able to implement a very small CPU but this limit will be hit pretty quickly I believe.

The other obvious limitation is the output of our system. Since the output must be triggerable by the monsters composing the system it can only be triggered from a teleporter, a lift, or a monster opening a door. With more modern source ports there are likely more options available. At the very least, you can use voodoo dolls and BOOM's conveyer belts to get a lot more interesting output. I have not looked into this in any way; this is pure speculation.

# Summary and Ramblings
Thanks for reading this far. To recap, we've seen how to implement some logic circuits using the original DOOM engine showing that it is even more extensible than intended. While, in my opinion, this is a pretty cool thing, I don't think it will have any practical use to the DOOM community. More recent source ports contain many useful features and mappers are incredibly creative with how they employ them. I think at best it might inspire some to look at boolean algebra (if they're not already familiar) to help lay out some aspects of their maps.

Some people may be wondering why I attempted this and it is as simple as I liked the idea. I don't quite remember why the idea popped into my head but a month or so ago I figured that DOOM was Turing-complete. I didn't do much with that thought for a bit and then slowly started trying to convince myself of it. A list of linedef actions was all I needed; I didn't even read any code. My only regret is not making more "does it run DOOM?" references.

Anyway, DOOM is a fun game. I recommend playing it if you can. Let me know if I made any mistakes, I'd love to hear of them and fix them if I can.
