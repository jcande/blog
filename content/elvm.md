Title: ELVM: The Esoteric-Language Virtual Machine Compiler
Date: 2020-5-26 16:29
Category: Spelunking in the Turing Tarpit
Tags: compilers; programming; esoteric
Slug: elvm
Authors: Jared Candelaria
Summary: Introduction to the ELVM project, including instructions for adding a new target.


[ELVM](https://github.com/shinh/elvm) is a project started by Shinichiro Hamaji in order to run a Lisp interpreter in brainfuck. It is now a welcoming project that seeks to expand its list of runnable programs, supported C features, and most interestingly its catalogue of backends. In this post I'll talk about the various features of the abstract machine and how to start implementing a backend for it.

This is part of a series on implementing a toolchain for a weird machine. See the [introduction]({filename}/tag_introduction.md) for more context.

[TOC]

## The ELVM Abstract Machine

As stated previously, ELVM started out as a way to compile C to brainfuck. This had the side-effect of enabling other similarly constrained "targets" to piggyback off the resultant infrastructure. But what infrastructure is there, precisely?

To start, ELVM defines a very simple abstract machine consisting of four general purpose registers (A, B, C, and D), along with BP, and SP. That's it. x86's lack of registers ain't got nothing on us.

The abstract machine is similarly aggressively RISCy in that it defines only: add, sub, mov, load, store, cmp, various jumps, exit, and of course: getc and putc. (There is also a "dump" instruction but that is essentially a freebie to help with debugging backends.) There are no floating point operations. There aren't even any multiplication or shift operations. We are about as bare-bones as you can get. But you'll note that it's got it all! There's conditional branching! The rest is mere fluff but even then it over-delivers with MATH, memory, even IO! We've definitely got a real computer.

I should expand on the instructions a bit. `getc` and `putc` are clearly meant for `stdin` and `stdout` in traditional esolang fashion. `mov` lets us edit registers. `store` and `load` grant us memory access addressible up to our machine's word size. `cmp` lets us perform various unsigned tests. We'll re-use most of this code for our implementation of conditional jumps. Finally, `add`, `sub`, and `exit` are convenience instructions. Oh yeah, `dump` is a nop.

I mentioned a word size but didn't define it. Traditional backends use a 24-bit (3-byte) words. This is not required so use whatever word size is most convenient for your backend. I used 16-bit words, for example. Keep in mind that the compiler expects `sizeof(char) == sizeof(int) == sizeof(void*) == 1`. This is probably pretty strange from more traditional standpoints. It simplifies our lives a great deal, however.

ELVM encapsulates all of this in the form of an ELVM Intermediate Representation, or EIR. This is assembly for the abstract machine. It is about what you would expect and even includes some familiar directives like `.text` (for the code section) and `.data` (for, well, the data section). This format is serialized and stored with the extension `.eir`; this is the input for the backends. It may seem unintuitive to "compile" from this low-level assembly-style language into a "high(er)"-level language but this just showcases the wonderful telescopic nature of computability! There is truly no "bottom" and we can burrow endlessly embedding more and more languages into themselves. Our job implementing the target backend is simply to implement the semantics of this abstract machine instruction-by-instruction however we are able.

Another nice thing about EIR is that it is "self-aware". I mean this in a literal and mind-bending sense as it allows us to embed "magic comments" which are essentially strings passed from one stage to the next. These magic comments have few restrictions, namely length and are nul-terminated, and no structure. You can use them to embed state from the other side to help with debugging. To use them simply enclose the text to transmit in curly braces ('{', and '}') in a comment. For example, `#{There is no escaping the simulacrum}`. These comments get attached to the subsequent instruction. You'll now be able to send one-off messages into the void.

One last thing to keep in mind is that this is a Harvard architecture. This means that code and data are separate. I mean completely separate. All memory that you can access will be yours to overwrite as the code does not live there. This isn't really a concern for most portable C code but it does rule out writing some interesting self-modifying code. On that note, the concept of instruction pointer or program counter is different than you're likely to run into elsewhere. You can think of every "basic block" as having the same PC. From the C code's perspective this shouldn't be a concern but it is something to know about.

Here's an example "hello world" program.

    # A comment starts with '#', like this.
    .text
        # Place the address of `greeting` into register A
        mov A, greeting

    # You can freely mix the section directives.
    .data
    greeting:
    # Strings are nul-terminated.
    .string "hello world\n"

    .text
        jmp test_for_null
    
    nonzero:
        #{Start of character-printing basic-block.}
        putc D
        add A, 1
    
    test_for_null:
        load D, A
        jne nonzero, D, 0
    
        # It's good manners to explicitly exit.
        exit

For more (and more concise) information, see [this ELVM](https://github.com/shinh/elvm/tree/c19d1e245d6760be8418df541abfc7122a28b9f7/ELVM.md).

## Target Acquired

Now that we understand the shape of the machine we are targeting, let's explore what exactly we need to do.

First off, we probably want to register our backend with the main compiler `elc`. To do this we'll have to add a command line switch in [target/elc.c](https://github.com/shinh/elvm/tree/c19d1e245d6760be8418df541abfc7122a28b9f7/target/elc.c). We should go ahead and add the file that will hold our implementation to [Makefile](https://github.com/shinh/elvm/tree/c19d1e245d6760be8418df541abfc7122a28b9f7/Makefile) by inserting it into the source list `ELC_SRCS`.

While we're in the Makefile, let's go ahead and define some other properties. The name of the binary sounds useful so add `TARGET := <binname>`. Look around the file and fill the rest out as is natural.

### Makefile Definitions

You may be asking yourself what exactly all of these variables are doing. For clarification, let's peek at `RUNNER` first. This variable defines a "runner" file that is responsible for executing the output of the compiler by the target. As a convenient example let's say that your target is some interpreted language. This runner would essentially run the interpreter and point it at the generated file. In some cases, we'll need to further process the output (e.g., you don't have an interpreter and need another compilation stage) so here is where we would place that logic.

Another interesting variable is `TOOL`. You can think of this as defining a dependency on some later stage of compilation necessary to run your target. In my case, I have some rust code. I used `TOOL := cargo` to neatly solve that.

The last one I'll cover is `TEST_FILTER`. This is essentially a list of tests to NOT run. If your backend has some quirks then you'll probably need to add some tests here. Otherwise, feel free to omit it. A good example use-case are targets that do not use 24-bit words excluding the tests that require 24-bit words.

Now we know enough to build. We can run `make` to build everything but this is terrible and will take hours. Instead we can do `make <target>` (e.g., `make c`) to build our target (and tests) in particular.

### EIR Interface

Our target must implement at least one function which is the callback we specified in [target/elc.c](https://github.com/shinh/elvm/tree/c19d1e245d6760be8418df541abfc7122a28b9f7/target/elc.c). To follow the norms of the project, this takes the form `target_<name>`. It takes a single parameter of type `Module*`. Before we look at that in minor detail let's do a small survey.

The ELVM infrastructure provides a convenient way to interact with the EIR. In the file [ir/ir.h](https://github.com/shinh/elvm/tree/c19d1e245d6760be8418df541abfc7122a28b9f7/ir/ir.h) lie a bunch of structures. You'll likely want to have this open while you are first starting out. Now I'll briefly list the structures and comment on how you'll be using them:

* `Module` - structure. This is the root that everything else hangs off of. This is type that our entrypoint receives as its only parameter. It is the whole world.
* `Data` - structure. This is a linked-list of words. You'll notice it does not contain the corresponding address so we'll need to keep track of that ourselves. The initial node corresponds to address 0.
* `Inst` - structure. This is the good stuff. Like data, a linked-list of instructions where each node represents a single EIR instruction. Contains the opcode, destination value, source value, jump destination addresss, and program-counter the instruction belongs to. I didn't describe all the fields. Also, each instruction will not necessarily use all of these fields.
* `Op` - enum. This just contains every operation we support (and a few we don't need to worry about). The jumps and comparisons are neatly aligned and symmetric.
* `Value` - tagged union. This is the structure that is used in most instruction's source and destination fields. It can either be an immediate value or an enum specifying the register containing the value.
* `ValueType` - enum. This is the tag specifying whether or not the `Value` is an `IMM`ediate or a `REG`ister.
* `Reg` - enum. Contains all the registers we can use.

The above alone should be enough for us to get started. Keep the definitions handy as you'll likely refer back to them regularly while setting up the skeleton of your target.

### Backend Case Study

Now we are finally ready to start writing some real code! Only instead of writing anything we'll simply analyze an implementation of the abstract machine in a very expressive language: C! This means we'll compile C to EIR and then from EIR into C. You might notice that the input C file and the last C file look essentially nothing alike. Let's see why by examining how the abstract machine is implemented.

We'll start at the beginning from `target_c` in [target/c.c](https://github.com/shinh/elvm/tree/c19d1e245d6760be8418df541abfc7122a28b9f7/target/c.c#L112). We immediately encounter `emit_chunked_main_loop`, our first ELVM API. The explanation for this one is involved but not complicated per se. We can note that it takes five parameters: the root of the instructions as a linked-list, and four functions. The functions consist of callbacks for prologue and epilogue pairs, basic-block transitions, and finally the instructions themselves. The last two should be fairly intuitive but what is up with being invoked for a function prologue and epilogue? Well, as far as I understand it, this is a layer of indirection introduced to minimize the size of any given PC-based lookup table. It is a performance optimization. Regardless, check out [the implementation](https://github.com/shinh/elvm/blob/c19d1e245d6760be8418df541abfc7122a28b9f7/target/util.c#L197) to see that it's not so complicated and basically just emits each instruction and some prologue/epilogue pairs every so often.

Jumping back to our entrypoint function, we then stumbled across [a loop over the data items](https://github.com/shinh/elvm/blob/master/target/c.c#L125). This is a list of words pulled from the `.data` section in the source EIR file. They implicit begin at memory address 0. This loop is responsible for initializing the memory of the ELVM abstract machine. We can do this anywhere we like so long as it occurs before any instructions are executed as they likely will reference memory.

Continuing down the source and we hit [another loop](https://github.com/shinh/elvm/blob/master/target/c.c#L135). This one is much more mysterious, however. Immediately before we see a reference to `CHUNKED_FUNC_SIZE` and inside the loop we are invoking a numbered function. We have a pretty good intuition that this is the "other side" of the layer of indirection that actually sets the whole machine in motion. Examing a bit more closely, there is a fragment `pc / CHUNKED_FUNC_SIZE` which effectively chunks every program-counter into buckets of size `CHUNKED_FUNC_SIZE`. This explains the implementation of `emit_chunked_main_loop`. Now we underestand that each chunked-function handles only `CHUNKED_FUNC_SIZE` instructions. This loop is how we dispatch the necessary chunked-function.

Now that we've taken care of most of the infrastructure, we can look at how to actually implement any given ELVM instruction. We note the initial invocation of `emit_chunked_main_loop` passed a callback that the caller refers to as `emit_inst`. It's the last argument to the function and we call it [`c_emit_inst`](https://github.com/shinh/elvm/blob/master/target/c.c#L44). Jackpot! Here we've got a nice switch over all of the instructions. Since C is so very expressive, each instruction is no more than a single line. Add any per instruction instrumentation you like here. To make debugging nicer you can even embed breakpoints to see exactly when each instruction in the abstract machine gets executed.

And that's it. Not so bad. Hopefully this proved useful for someone. Good luck implementing your compiler.
