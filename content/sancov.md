Title: SanCov: Above and Below the Sanitizer Interface
Date: 2020-9-17 15:03
Category: reference
Tags: compilers; programming; security
Slug: sanitizer-coverage-interface
Authors: Jared Candelaria
TwitterName: @jsc29a
Summary: Modern compilers provide a great mechanism to provide developers convenient access to program details in the form of various sanitizers. This post will discuss some aspects of that interface.

In the everlasting struggle to rid the world of bugs, compilers are being deployed in interesting ways. One particularly interesting development is "standard" instrumentation that can be used to automatically discover bugs during runtime for native programs. One of the primary means to accomplish this is through novel applications of [code coverage](https://en.wikipedia.org/wiki/Code_coverage) instrumentation. These raw primitives are general and can be extended by an application developer implementing various callbacks.

More simply, the compiler generates code which calls into the sanitizer coverage (SanCov) interface. These callbacks must be implemented by someone. Default implementations exist in [compiler-rt](https://compiler-rt.llvm.org/). The user can override them. [The sanitizer coverage documentation](https://clang.llvm.org/docs/SanitizerCoverage.html) provides descriptions and example code.

To provide some context, I wanted to see how this interface was used in practice. I'll talk about what the compiler is doing underneath the interface as well as what a consumer receives above the interface. The compiler I'm using is [clang](https://clang.llvm.org/) and the consumer is the fuzzer [honggfuzz](https://honggfuzz.dev/).

If you are familiar with fuzzing in general then feel free to jump right to [an explanation of the sanitizer coverage interface](#sanitizer-coverage-interface-overview).

[TOC]

# Motivation
I understand you are aware that we're trying to find bugs and so what more motivation could we need? But I think before jumping right in, there is some history that might be helpful. Fuzzing is a wide field with a lot of neat technical insights and tricks up its sleeve. It is essentially a style of software testing that tends to involve a nice handful of randomness. One important aspect of it is actually creating the tests (as opposed to running them, and verifying the results).

We can wear a monocle and say this "automatic test case generation" can be accomplished in a few ways. We can attempt to describe the range of all inputs, perhaps by some specification. We would then implement a tool to sample these possible results. The obvious downsides are that the specification can be quite large, incomplete, and/or distinct from the implementation. But what can you do? Another approach could be to collect a giant trove of inputs. Once we have a hoard fit for a dragon we could run various passes over our collection and feed them one at a time into the target. Some of the downsides here are needing to collect the samples up front, knowing if our collection is of high enough quality (whatever that might entail), and being fairly static. These are honestly really good approaches but there is always room for improvement, or at least alternative methods with their own tradeoffs.

What other way could we attempt to approach this problem? What is a downside both approaches share? Throughout many aspects of day to day life there exist various assessment mechanisms. You receive grades, reviews, awards, and fines. You give ratings, comments, and feedback. The previous approaches didn't really have any feedback. How could you tell that a sample was better than any other? Samples producing crashes (guaranteed bugs) seem better than those that don't. True! But we can refine them even more. Consider that most malformed samples "bail out early", meaning they quickly produce an error and the program safely exits. In this way, samples that can reach "deeper" are more likely to "trigger", "hit", or "uncover" a problem, if we assume bugs are evenly distributed (which isn't likely but helpful to illustrate the point). To continue this line of thought, one eventually needs to measure a given input. We can choose code coverage as the metric for this depth. This is the intuition needed to understand feedback driven fuzzing. We can honestly use any metric we like but code coverage is a pretty useful starting point.

Also, this description has been incredibly narrow in its focus and only discusses "file format fuzzing". This means that it implicitly refers to programs that can be decomposed into:
1) Read data
2) Parse data
3) Return Results
This covers quite a lot of ground (think PDF readers, office documents, image renderers, etc) but is less helpful for other aspects of programs. Stateful things, servers, and other components that break the previous mold will resist naive attempts at fuzzing. There is hope! But that is outside of the scope for this article as we're talking about sanitizers and not fuzzing directly.

## Terminology
Since we're talking about an interface provided by the compiler we'll have to know what the compiler people care about. They encode their hopes and dreams in strange jargon but as empathetic beings we can meet them half-way.

We are all vaguely aware that a "high-level" language is decomposed-into/implemented-by smaller atomic units. For convenience, let's take these units to be the instructions making up the underlying interpreter that is the CPU. Focusing on individual instructions is not particularly useful for our context. Instead we can group them into collections that are all executed as a unit. To give some example, you can imagine that the body of an if-statement constitute this collection (ignoring nested ifs, and other more complicated cases). This is the intuition behind what the compiler people refer to as a [basic block](https://en.wikipedia.org/wiki/Basic_block).

A program can be viewed as a [graph](https://en.wikipedia.org/wiki/Control-flow_graph) with basic blocks as the nodes. We can query this graph to answer various questions about it. What questions do we have? To start, we'd like a way to obtain the code coverage for a given input. This can be done by attaching a boolean to each node (basic block) initialized to False, as nothing has been reached yet. As we execute the program on a given input we can set the boolean for the node corresponding to the current instruction pointer to True, as it was actually touched. At the end, we can filter the nodes that weren't executed. This is our coverage map.

There are some obvious deficiencies in this approach. We are only storing whether or not a given block is ever executed. It might be interesting to see how many times a block is executed. And since we're talking about the program as a graph, we are completely ignoring how each node is connected--the <strong>edges</strong>. In fact, we can ignore the nodes and count the edges instead. This is a much richer source of information.

## Background
All of these fuzzing developments happened over a pretty long time. I am not a historian, if you can believe that, and even more am not informed of the history. I have the layman's big-picture-that's-mostly-wrong understanding of things. Without polluting your mind too much, I'll narrow the focus to a singular moment (from my perspective). And that is when lcamtuf published an almost inscrutible monolith of C but packaged up in the most user friendly manner possible. I am referring, of course, to the release of American Fuzzy Lop better known as [AFL](https://lcamtuf.coredump.cx/afl/).

AFL "employs a novel type of compile-time instrumentation and genetic algorithms to automatically discover clean, interesting test cases that trigger new internal states in the targeted binary". Essentially magic. It's absolutely packed with awesome stuff. A fake compiler that not only injects instrumentation but also sets compilation flags to make the binary more sensitive to memory corruption. A fuzzing harness that does everything you would want with the benefit that you don't have to code it yourself. A UI that makes you truly feel like you are a hacker. And, of course, automatic test case generation with feedback via code coverage as its fitness function.

[The technical details of AFL](https://github.com/mirrorer/afl/blob/master/docs/technical_details.txt) are extensively well documented by the author. I won't attempt to explain them here. Please read them if you haven't; you won't regret it. Similarly, [read the historical notes provided by the same author](https://lcamtuf.coredump.cx/afl/historical_notes.txt) as they're great!

# Sanitizer Coverage Interface Overview
Now that we have some familiarity with the problem we intend to solve, let's see how the industry/community resolved it. Namely, we now come to the SanCov interface. I have no clue what the name for this actually is but hopefully this is descriptive enough. Essentially, the compiler inserts some instrumentation at the necessary places in the binary of our program that performs some of the bookkeeping tasks described above. They've done one better even, and will let the application developer customize the functionality.

To enumerate the interface functions that we'll talk about we have:

* [\_\_sanitizer\_cov\_trace\_pc](#__sanitizer_cov_trace_pc) - basic block
* [\_\_sanitizer\_cov\_trace\_pc\_guard\_init](#__sanitizer_cov_trace_pc_guard_init) - "guard" initialization
    * [\_\_sanitizer\_cov\_trace\_pc\_guard](#__sanitizer_cov_trace_pc_guard) - guards themselves
    * [\_\_sanitizer\_cov\_trace\_pc\_indir](#__sanitizer_cov_trace_pc_indir) - indirect branches
* [\_\_sanitizer\_cov\_8bit\_counters\_init](#__sanitizer_cov_8bit_counters_init) - counter initialization

We can see the outline of some familiar ideas. We have a callback for basic blocks as to be expected but we also see some specificity that was never mentioned with the indirect branching callback. There are also completely alien things like guards. The counter idea doesn't seem too far fetched, though. There are also plenty of other nice APIs that I won't cover but you can explore by reading [the LLVM documentation for SanitizerCoverage](https://clang.llvm.org/docs/SanitizerCoverage.html).

## Guards
Ok so we have the concept of "guards". What are they? From [the LLVM sancov documentation mentioning guards](https://clang.llvm.org/docs/SanitizerCoverage.html#tracing-pcs-with-guards), we learn that a guard is a unique id for some object. In other words, every edge will have a corresponding guard variable. We will assume a guard variable is of type uint32\_t and is strictly greater than 0. Let's just think of them as indices.

# Sanitizer Coverage Interface in Practice
Now that we have a rough idea of the pieces, we need to understand the contract between the compiler and the runtime. We want to examine how honggfuzz interprets the provided data but we also want to see how to generate that data in the first place as well as when to actually hand it over. Below are explanations of the interface along with examples generated by clang.

The format will include the compilation flag to emit the corresponding feature being discussed, a brief summary of the feature itself, summary of how honggfuzz actually consumes the data, and finally the compiler source and output with some commentary.

## Demonstration Code
Oh right, and because we actually need some data in the form of a program we'll use the below which should handle all of the cases we are concerned with.

    int a(void)
    {
        return 1;
    }
    int b(void)
    {
        return 2 + a();
    }
    int c(void)
    {
        int value = b();
        switch (value) {
        case 3:
            return value;
        case 2:
            return value;
        case 1:
            return value;
        default:
            return 0;
        }
    }
    int d(void)
    {
        int value = c();
        if (value > 0) {
            value -= 1;
        } else {
            value += 1;
        }
        return value;
    }
    
    int main(int argc, char** argv)
    {
        int(*table[])(void) = {
            a,
            b,
            c,
            d
        };
        if (argc < 4) {
            return table[argc]();
        } else {
            return -1;
        }
        return 0;
    }

Now we can finally get our hands dirty.

## __sanitizer_cov_trace_pc
Compilation flags: `-fsanitize-coverage=trace-pc`

This will be invoked at the beginning of every basic block, not every PC as you might expect. The information is not lost as we can infer every PC from this data and it saves execution time (which adds up).

[Honggfuzz runtime](https://github.com/google/honggfuzz/blob/598d1f9e5cec91e7a0c2cd8f5a7e164508fc6e1e/libhfuzz/instrument.c#L299)

The data is used to consult a bitmap to mark "hit" blocks. If this is a new block, it similarly increments an "interesting events this run" counter.

[Compiler Source](https://github.com/llvm/llvm-project/blob/6a822e20ce700f2f98e80c6ce8dda026099c39b7/llvm/lib/Transforms/Instrumentation/SanitizerCoverage.cpp#L918) and [Compiler Output](https://godbolt.org/z/fTK8GE)

As you can see, most basic blocks contain a call to `__sanitizer_cov_trace_pc`. The blocks that don't correspond to something like a single "idea" in C, like the switch-statement in the c() function.

## __sanitizer_cov_trace_pc_guard_init
Compilation Flags: `-fsanitize-coverage=trace-pc-guard`

As you can imagine, the intent behind `__sanitizer_cov_trace_pc_guard_init` is to initialize the backing array corresponding to each guard. See [the LLVM documentation](https://clang.llvm.org/docs/SanitizerCoverage.html#tracing-pcs-with-guards) for more details.

[The honggfuzz runtime](https://github.com/google/honggfuzz/blob/598d1f9e5cec91e7a0c2cd8f5a7e164508fc6e1e/libhfuzz/instrument.c#L563)

This takes an array [start, end) of uint32\_t guards. It will populate each guard with its guard number (guardNo) for later use. Essentially it writes sequential nonzero values as obtained from `instrumentReserveGuard`. Later, it uses these values as indices into other statistics tables. If, for some reason, it no longer needs a guard it will zero its guard number and any further calls using this guard will be ignored.

[Compiler Source](https://github.com/llvm/llvm-project/blob/6a822e20ce700f2f98e80c6ce8dda026099c39b7/llvm/lib/Transforms/Instrumentation/SanitizerCoverage.cpp#L497) and [Compiler Output](https://godbolt.org/z/dTG838)

Look at the assembly output terminating on line 157. We load the start and end of some array into rdi (first argument) and rsi (second argument) before invoking `__sanitizer_cov_trace_pc_guard_init` as you'd expect. The compiler allocates the array. One thing to note is that this is a module constructor and so is guaranteed to be run before non-constructor code. The implementation depends on pretty intense Implementation Specific details such as the loader but if you think of the general idea of pre- and post-execution hooks, a constructor would be pre-execution.

### __sanitizer_cov_trace_pc_guard
This is invoked at the beginning of every basic block. The interesting thing about this is that we give it a pointer to a "guard". This guard-ptr is UNIQUE per EDGE. That means the runtime can track edge-specific state which is much richer than a simple hit bitmap.

[The honggfuzz runtime](https://github.com/google/honggfuzz/blob/598d1f9e5cec91e7a0c2cd8f5a7e164508fc6e1e/libhfuzz/instrument.c#L602)

Honggfuzz uses this to update a bunch of statistics. If a guard is 0 it is considered uninteresting and so doesn't impact any further statistics. We decide if a guard is uninteresting if we've traversed the edge it describes more than 100 times. The first time we see the edge (`localCovFeedback->pcGuardMap[*guard_ptr] == 0`), however, we increment pidTotalEdge to keep track of how many new edges we've seen. Otherwise it increments pidTotalCmp. Then, it implements a step-function of the edge-count. As the edge-count surpasses the current step we count it as a new edge, otherwise we treat it as a feature (i.e., cmp).

[Compiler Source](https://github.com/llvm/llvm-project/blob/6a822e20ce700f2f98e80c6ce8dda026099c39b7/llvm/lib/Transforms/Instrumentation/SanitizerCoverage.cpp#L488) and [Compiler Output](https://godbolt.org/z/dTG838)

You'll see many invocations of `__sanitizer_cov_trace_pc_guard` and they all use constant values (e.g., `.L__sancov_gen_.1`). These correspond to specific elements in that array that was passed into `__sanitizer_cov_trace_pc_guard_init`. We can think of this as corresponding to names for each edge and this is how we can sense which edges are executed and in which order.

### __sanitizer_cov_trace_pc_indir
Compilation flags: `-fsanitize-coverage=trace-pc-guard,indirect-calls`

This is essentially the same as [\_\_sanitizer\_cov\_trace\_pc](#__sanitizer_cov_trace_pc) but only covering indirect branches.

[The honggfuzz runtime](https://github.com/google/honggfuzz/blob/598d1f9e5cec91e7a0c2cd8f5a7e164508fc6e1e/libhfuzz/instrument.c#L532)

This is a pretty interesting example because it mixes the destination address (named `callee` in the sources) with the source address (well, it is really the address immediately before the indirect call because `__builtin_return_address(0)` is the return address). The function is only interested in the offset of `callee` (the low 3 nibbles hence `0xfff`). Not coincidentally it shifts up the source address by 12, which fits exactly. This sounds a bit vague, so let's use an example. Given a source address of `0xAABBCCDD` and destination of `0xUUVVWxyz`, we get the mixed value of: `(0xAABBCCDD << 12) | (0xUUVVWxyz & 0xff)` or `0xBCCDDxyz`. This example uses a 32-bit address space but it will work with larger values.

Now the question remains, what is the point of that? I can't speak to the exact reasons the developer would give but I can add some speculation. The source address is mostly preserved, including its offset. The high bits might be very similar for all code located in the same "object" (for lack of a better term, but think library or main binary), and in this way not much information is actually lost in practice. Perhaps these dynamic dispatch locations have some strange properties or maybe it helps to see them when debugging. As for the destination, we only care about its offset. I'm not really sure why this mixture is performed but the general idea of mixing the two values is to create a unique guard that distinguishes between source->destination and destination->source.

Now the REAL question remains, what? We're just trying to make a guard (i.e., a unique index). We can ignore the specific implementation and simply think of this as a quick hash function.

[Compiler Source](https://github.com/llvm/llvm-project/blob/6a822e20ce700f2f98e80c6ce8dda026099c39b7/llvm/lib/Transforms/Instrumentation/SanitizerCoverage.cpp#L775) and [Compiler Output](https://godbolt.org/z/T4KsYx)

Ok this one will require a bit of an explanation. The only bit of code in the example that has an indirect branch is the function table in main (C source, line 44). Briefly, we use `argc` as an index. `argc` is also the first parameter to main, so it goes in the register rdi (in this calling convention), which gets saved into the stack at line 113 into `rbp-52`, retrieved at line 133 into rcx, and promptly stored once more at `rbp-8` (-O0 doesn't mess around). Skipping over the initialization of the table, we then retrieve `argc` from the stack at line 136 and save it into rax and use it to retrieve the function pointer from the table and store it into rdi, the first argument. We then invoke `__sanitizer_cov_trace_pc_indir`. As we can see, we pass the target address (i.e., the value of the function pointer that was calculated indirectly) to `__sanitizer_cov_trace_pc_indir`.


## __sanitizer_cov_8bit_counters_init
Compilation flags: `-fsanitize-coverage=inline-8bit-counters`

This combines the guard idea with a counter. Every basic block gets a corresponding counter. Every time we hit a block, we increment its counter. See [the LLVM documentation on 8-bit counters](https://clang.llvm.org/docs/SanitizerCoverage.html#inline-8bit-counters) for more information.

[The honggfuzz runtime](https://github.com/google/honggfuzz/blob/598d1f9e5cec91e7a0c2cd8f5a7e164508fc6e1e/libhfuzz/instrument.c#L713)

This takes an interesting approach and has a per Dynamic Share Object (DSO, think .so/.dll) counter group. It tracks this with a guardNb (guard number) variable and increments it (up to the limit) every time this counter_init routine is invoked so that it can later (at the end of the run) iterate over all the counters to tally up some statistics. It assumes the counters use the same guard as `__sanitizer_cov_trace_pc_guard`.

The special aspect is that outside of the initialization, there is no explicit function we can call to transfer information. At any single point in time, examining the counts will show us how many times the corresponding edge has been executed as the compiler automatically inserts increments as appropriate just like with `__sanitizer_cov_trace_pc_guard`.

[Compiler Source](https://github.com/llvm/llvm-project/blob/6a822e20ce700f2f98e80c6ce8dda026099c39b7/llvm/lib/Transforms/Instrumentation/SanitizerCoverage.cpp#L501) and [Compiler Output](https://godbolt.org/z/rb64KM)

Just like `__sanitizer_cov_trace_pc_guard_init`, we setup another array that corresponds to hit counters for the instrumented edges. In the compilation output we can see we (really explicitly, thanks to -O0) retrieve the value into al, increment it by 1, and store it back into the proper slot (e.g., `.L__sancov_gen_.1`).

# Wrapping Up
Hopefully this has been a helpful overview of some ideas behind sanitizers. Now you should be able to implement both sides of the interface. You can generate guards to pass into consumers, or handle calls from arbitrary programs. If you want to instrument an emulator you can now add the proper calls to the equivalent runtime consumer by mimicking the approach LLVM took. If you'd like to create your own fuzzer and take advantage of compiler instrumentation, you should be able to crib from honggfuzz.

Similarly, you can now abuse the interface and get a nice genetic fitness framework by manipulating the various fuzzers that consume the sancov data!
