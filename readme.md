# Pre-preprocessor compiler extension

## The Necessity which is the Mother of this Invention

(First person in the perspect of the primary/original person writing this forward.)  

I write microcontroller based devices in assembly, primarily in the Microchip PIC18 line of microcontrollers using the MPASM compiler.  I've written enough variations based on the same system that I've built a framework for my system.  My framework is essentially a little operating system, but very spartan and requires modifications to my framework files everytime I build a new device on my framework.  

For any new module that I base on my existing framework, there are sections of code that need to inserted into various places in what is essentially the operating system sections.  Currently, my process is to select a code word for the new module and then modify all the framework files to include macros related to the sections of inserted of code when the project's code word is _defined_.  

A tedious problem in this approach is that I have to modify my base framework files for every new module I create.  Since these framework files are shared with all existing projects, I have to be careful to not break previous projects.  

To steamline and improve scaleability of this process, I propose the following preprocessor mechanism...  

## The "SECTION" preprocessor directive

### Basic definition

Within a library or framework file, there is a preprocessor directive of a named "#SECTION".  Its arguments are the name of the section, and then optional arguments that are passed to the macros that will be inserted at that point.  

Before the "#SECTION" directive, there must be defined pieces to insert into that section.  (If not, the 'section' is left empty.)  This is the "#INSERT" directive.  The INSERT directive is given arguments of a macro to insert, the name of the SECTION to insert it to, and optionally an integer number to affect the priority ordering of this INSERT related to other INSERTs destined for the same SECTION.  Lower numbers have a higher priority (thus are inserted first), and there is no defined method for determining priority on sections given the same priority value.  

All INSERT directives must come before the related SECTION directive.  It will be an error to declare an INSERT directive after its related SECTION directive.  After transversing the entire project, it is highly suggested that it be an error to have INSERT directives that have not been inserted into a SECTION.  

The reason that the INSERT directive will only take a 'macro' name as an argument is that it simplifies the pre-preprocessing logic, but allows arbitrary length sections to be inserted, along with supporting the variable substitution facilities handled by the macro directive.  

### The convention in practice

In your project, framework files must be included after all relevant project files which define macros to insert.

For example, the following section of code to be inserted in a system area is shown below.

```
custom_project_isr_section macro portname
    ; handle this project's business during the Interrupt Service Routine
    movlw       0x88
    movwf       portname
    endm

#INSERT custom_project_isr_section framework_isr_section 5
```

The above defines a macro "custom_project_isr_section" which will be inserted at a section named "framework_isr_section".  At this section, the macro name will be inserted into the code.  If there are other macros inserted into the same section, this one will have a priority of '5'.  The lower number has a higher priority and will be stacked first in the SECTION section.  The default priority is '100'.

```
#SECTION framework_isr_section LATA
```

The above declaration will cause the pre-preprocessor to replace it with the macro "custom_project_isr_section" and give that macro the argument of "LATA", as shown below.  This particular SECTION declaration is presumably with framework library file that handles the Interrupt Service Routine.  

```
    custom_project_isr_section LATA
```

If there was more than one INSERT directive naming the same SECTION, multiple macro names will be placed there.  

As an added option, the INSERT directive will take macro arguments after the priority value.  (Thus, you must specify the priority value.)  In such usage, the SECTION should not have arguments for the macro.  When expanded into the SECTION, the macro's arguments will come from the INSERT directive.  

Thus, the general forms are:

```
#INSERT (macro_name) (section_name) [priority] [macro_arg [macro_arg] [...]]
#SECTION (section_name) [macro_arg [macro_arg] [...]]
```

## The "GENERATE" preprocessor directive

A further problem I've had with limitations in the MPASM is the inability to use the "#v(expr)" operation to generate sequential names that are passed to conditional directives.  (Section 7.4 of the MPASM user's guide.)  Thus, I added in the GENERATE directive.  

This directive with its closing directive ENDGEN contains a block of code that is repeated a number of times and in each repetition, the number from the loop sequence can be substituted into the text.  The substitution variable is set between curly braces.  Currently, the code only supplies basic substitution.  If the variable is a single 'i', the current count number is used.  If the variable have been DEFINEd, then that is used.  Lastly, if the variable is multiple 'i's, then the count number is extended with zeros on the front until it's as long as the length of 'i's.

Thus, the general form is:  

```
#GENERATE (start_number) (end_number)
some code block
some number that needs substitution here {i}
some number {iiii} that you want to be at least four digits long
something that has been #DEFINE'd {defined_var} goes here
some more code
#ENDGEN
```

The range numbers are taken as decimal integers and generate a range inclusive to both limits.  An example usage is as follows...

```
#GENERATE 5 7
#IFDEF pin_{i}_exists
    bcf   main_port, {i}
#ELSE
    bsf   register, {i}
#ENDIF

#ENDGEN
```


## A "pre-preprocessor" program to handle this convention

Until this convention can included in an official assembler, this project is to build a pre-preprocessor that interprets and replaces these directives so that the official assembler for any particular architecture can be used with this functionality.  

This pre-preprocessor will need to interpret and execute most of the #DEFINE and #IFDEF directives because of their bearing on INSERT and SECTION directives.  

Currently, this project converts the project and all its included files into a single temporary file that is passed to the main assembler.  This keeps it from modifying the main files, but makes finding the original source code that causes errors raised by the final assembler harder to find.  

The current way of inserting this into your tool chain is to rename your original assembler program, provide a link from what its name was to this program, and then configure this program to know where your original assembler is so that it may chain to it.
