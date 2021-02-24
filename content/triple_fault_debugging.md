Title: Fault Oriented Debugging
Date: 2020-12-21 12:00
Category: reference
Tags: debugging; firmware; programming; esoteric
Slug: triple-fault-debugging
Authors: Jared Candelaria
TwitterName: @jsc29a
Summary: Niche trick to abuse a simulator into giving useful debug information.

For various reasons I was working on some firmware running on a 486. The environment I had was a test suite that used a simulator. The tests would compare memory dumps to ensure bit perfect accuracy. And that's all I had to go on. I was unable to inspect the machine state in the simulator; I could just see if the tests passed or failed. As you can imagine, it was not the most conducive environment for debugging.

One nice and unexpected quirk of the simulator was that it would print out a message if it triple-faulted. The information contained was minimal, consisting only of faults (e.g., #GP, #SS, #SS) and the physical address of the faulting instruction followed by the raw bytes comprising the instruction. Unfortunately no register state was provided.

At first, I ignored this. My working loop was to make a slight change, see if the tests passed, and if not sit and brood until I had a theory. Eventually this became untenable for my sanity and I started looking at quicker ways to get feedback.

Eventually I realized I could use the triple fault message as a non-interactive debugger. I'd have to encode my theories up front but since the environment was deterministic it wouldn't be a big deal. My first solution was to destroy the stack and trigger a fault which would cascade into a triple fault. I could then use this as an assert and could even have multiple asserts, differentiating between them from their physical addresses.

This worked but made printing out painful as I would basically be bitbanging over individual runs of the simulator. I could implement a trie to print out more than a single bit at a time but if I wanted to print out 32-bits I would still have to do multiple runs.

It was here that I realized I was under-utilizing my output buffer. The error message prints out the entire instruction. Instead of using the trie to navigate the output bit by bit, I could just encode it into the faulting instruction. To achieve this I added a new segment sharing the offset of the code segment, but writeable. I then set the stack to an invalid value, and executed the dynamic faulting instruction.

Here's the code to do this:

    :::asm
    #define TRIPLE_FAULT_PRINT(Value)   \
        asm(                            \
            "movl $0, %%esp\n"          \
            "movl %0, %%gs:2f\n"        \
            "1: .byte 0x68\n            \
            "2: .long 0x24242424\n"     \
            :                           \
            : "ir"(Value)               \
            :                           \
            )

This uses the fact that 0x0 is an invalid value for the stack. The faulting instruction encodes (initially) to `push 0x24242424`, which attempts to write to the stack and blows up. The constant it pushes is set dynamically.

I was able to use this trick in combination with the assert-like triggers to print out registers which helped with debugging.
